import math
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import xml.etree.ElementTree as ET

import numpy as np

from .BaseRobot import BaseRobot


class VirtualRobot(BaseRobot):
    """
    基于 MuJoCo 的虚拟机械臂：
    - 加载 MJCF/URDF（需要 MuJoCo 支持），提供关节/末端状态反馈
    - 支持按队列下发的关节/位姿命令（位姿经简单阻尼 IK 解算），末端执行器直写 ctrl
    - 以设定帧率触发 pose/joint/end_effector 事件，兼容现有遥操组
    """

    name = "Virtual Robot (MuJoCo)"
    description = "使用 MuJoCo 加载 URDF/MJCF 的虚拟机械臂"
    need_config = {
        "package_path": {
            "description": "URDF 包根目录（含 urdf/ 与 meshes/）",
            "type": "string",
        },
        "urdf_path": {
            "description": "URDF 文件相对路径（可选，未提供则自动搜索）",
            "type": "string",
            "default": "",
        },
        "fps": {
            "description": "反馈帧率",
            "type": "int",
            "default": 60,
        },
        "enable_gravity": {
            "description": "是否启用重力（默认关闭）",
            "type": "bool",
            "default": False,
        },
        "enable_gui": {
            "description": "是否启用仿真 GUI（默认关闭）",
            "type": "bool",
            "default": False,
        },
        "control_mode": {
            "description": "0: 位姿相对；1: 位置相对+姿态绝对；2: 位姿绝对",
            "type": "int",
            "default": 0,
        },
        "dof": {
            "description": "关节自由度数量",
            "type": "int",
            "default": 7,
        },
        "end_effector_site": {
            "description": "末端位姿读取的 site 名称（可选）",
            "type": "string",
            "default": "",
        },
    }

    def __init__(self, config: Dict[str, Any]):
        self.mujoco = None
        self.model = None
        self.data = None
        self.fps = 60
        self.dof = 7
        self.end_effector_site = ""
        self._ee_site_id: Optional[int] = None
        self._ee_body_id: Optional[int] = None
        self._controlled_dofs = self.dof
        self.enable_gravity = False
        self.enable_gui = False
        self._viewer = None
        self._default_gravity = None
        self.control_mode = 0
        self._prev_tech_state = None
        self._first_pose = None
        self._first_tech_state = None
        self.min_interval = 1.0 / self.fps
        self._time_counter = 0
        self.control_thread = None
        self.control_thread_running = False
        self._control_lock = threading.Lock()
        self._target_pose: Optional[list] = None
        self._target_end_effector: Optional[float] = None
        super().__init__(config)

    def set_config(self, config: Dict[str, Any]) -> bool:
        # 先补齐默认值再调用基类校验，避免缺少 dof/fps 时报必需字段缺失
        merged = dict(config) if config else {}
        for key, spec in self.need_config.items():
            if key not in merged and isinstance(spec, dict) and "default" in spec:
                merged[key] = spec["default"]
        if "enable_gravity" not in merged and "enable_physics" in merged:
            merged["enable_gravity"] = bool(merged["enable_physics"])

        super().set_config(merged)
        self.package_path = merged["package_path"]
        self.urdf_path = (merged.get("urdf_path") or "").strip()
        self.fps = int(merged.get("fps", self.fps))
        self.enable_gravity = bool(merged.get("enable_gravity", False))
        self.enable_gui = bool(merged.get("enable_gui", False))
        control_mode = int(merged.get("control_mode", 0))
        if control_mode not in (0, 1, 2):
            raise ValueError("control_mode 仅支持 0、1、2")
        self.control_mode = control_mode
        self.dof = int(merged.get("dof", self.dof))
        self.min_interval = 1.0 / self.fps if self.fps > 0 else 0.01
        self.end_effector_site = merged.get("end_effector_site", "") or ""
        self._controlled_dofs = self.dof
        self._joints = [0.0] * self.dof
        return True

    def _connect_device(self) -> bool:
        """加载 MuJoCo 模型"""
        try:
            import mujoco
        except ImportError as e:
            raise ImportError("需要安装 mujoco 以使用 VirtualRobot") from e

        self.mujoco = mujoco
        self.model = self._load_mujoco_model(self.package_path, self.urdf_path)
        self.data = mujoco.MjData(self.model)
        self.mj_step = mujoco.mj_step
        self.mj_forward = mujoco.mj_forward

        # 取模型 DOF 为主，避免配置与模型不一致
        self.dof = self.model.nq
        self._controlled_dofs = min(self.dof, self.model.nq, self.model.nv)
        self._ee_site_id, self._ee_body_id = self._resolve_end_effector_refs()
        self._default_gravity = np.array(self.model.opt.gravity, dtype=float)
        if not self.enable_gravity:
            self.model.opt.gravity[:] = 0.0
        if self.enable_gui:
            try:
                import mujoco.viewer

                self._viewer = mujoco.viewer.launch_passive(self.model, self.data)
            except Exception as e:
                self.emit("error", f"启动 MuJoCo GUI 失败: {e}")
        return True

    def _disconnect_device(self) -> bool:
        self.stop_control()
        if self._viewer is not None:
            try:
                self._viewer.close()
            except Exception:
                pass
            self._viewer = None
        self.model = None
        self.data = None
        self.mujoco = None
        return True

    def _main(self):
        """按帧推进仿真并发布最新状态"""
        if self.model is None or self.data is None:
            time.sleep(0.1)
            return

        last_time = time.time()
        self._time_counter += 1

        with self._control_lock:
            self.mj_step(self.model, self.data)
            joints = self.data.qpos[: self._controlled_dofs].tolist()
            pose, _ = self._get_end_effector_pose(return_mat=True, lock_already_held=True)
            ee_state = self._get_gripper_state(lock_already_held=True)

        if joints:
            self.current_joint_data = joints
            self.emit("joint", joints)

        if pose:
            self.current_pose_data = pose
            self.emit("pose", pose)

        if ee_state is not None:
            self.current_end_effector_data = ee_state
            self.emit("end_effector", [ee_state])

        if self._viewer is not None:
            try:
                self._viewer.sync()
            except Exception:
                pass

        if self.fps > 0:
            elapsed = time.time() - last_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)

    def _get_end_effector_pose(
        self, return_mat: bool = False, lock_already_held: bool = False
    ) -> Tuple[Optional[list], Optional[np.ndarray]]:
        """返回 [x,y,z,r,p,y] 以及（可选）旋转矩阵，若未配置 site 则使用末端所属 body"""
        if self.model is None or self.data is None:
            return None, None

        mat = None
        pos = None

        def _read_pose():
            nonlocal pos, mat
            if self._ee_site_id is not None and self.model.nsite > 0:
                pos = np.array(self.data.site_xpos[self._ee_site_id])
                mat = np.array(self.data.site_xmat[self._ee_site_id]).reshape(3, 3)
            else:
                body_id = self._ee_body_id if self._ee_body_id is not None else 0
                pos = np.array(self.data.xpos[body_id])
                mat = np.array(self.data.xmat[body_id]).reshape(3, 3)

        if lock_already_held:
            _read_pose()
        else:
            with self._control_lock:
                _read_pose()

        if pos is None or mat is None:
            return None, None

        rpy = self._mat_to_rpy(mat)
        pose = [float(pos[0]), float(pos[1]), float(pos[2]), *rpy]
        return (pose, mat) if return_mat else (pose, None)

    def _mat_to_rpy(self, mat: np.ndarray) -> list:
        """旋转矩阵转 RPY"""
        sy = math.sqrt(mat[0, 0] * mat[0, 0] + mat[1, 0] * mat[1, 0])
        singular = sy < 1e-6
        if not singular:
            roll = math.atan2(mat[2, 1], mat[2, 2])
            pitch = math.atan2(-mat[2, 0], sy)
            yaw = math.atan2(mat[1, 0], mat[0, 0])
        else:
            roll = math.atan2(-mat[1, 2], mat[1, 1])
            pitch = math.atan2(-mat[2, 0], sy)
            yaw = 0
        return [roll, pitch, yaw]

    def _rpy_to_matrix(self, roll: float, pitch: float, yaw: float) -> np.ndarray:
        cr, sr = math.cos(roll), math.sin(roll)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)

        return np.array(
            [
                [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                [-sp, cp * sr, cp * cr],
            ]
        )

    def _rotation_error(self, current: np.ndarray, target: np.ndarray) -> np.ndarray:
        """将旋转误差映射为轴角向量（弧度）"""
        r_err = target @ current.T
        trace = np.trace(r_err)
        trace = max(min((trace - 1.0) / 2.0, 1.0), -1.0)
        angle = math.acos(trace)
        if angle < 1e-6:
            return np.zeros(3)
        axis = np.array(
            [
                r_err[2, 1] - r_err[1, 2],
                r_err[0, 2] - r_err[2, 0],
                r_err[1, 0] - r_err[0, 1],
            ]
        )
        axis = axis / (2.0 * math.sin(angle))
        return axis * angle

    def _get_gripper_state(self, lock_already_held: bool = False):
        """简单返回末端第一个 actuator 的 ctrl 值或 0.0"""
        if self.model is None or self.data is None:
            return 0.0

        def _read_ctrl():
            if self.model.nu > 0:
                return float(self.data.ctrl[0])
            return 0.0

        if lock_already_held:
            return _read_ctrl()
        with self._control_lock:
            return _read_ctrl()

    def start_control(self, state=None, trigger=None):
        """开始控制：启动控制线程读取最新命令写入qpos/ctrl"""
        if self.is_controlling:
            return
        self.is_controlling = True
        self.control_thread_running = True
        # 进入控制时记录初始状态，后续用手柄差值叠加到机械臂初始值
        with self._control_lock:
            self._prev_tech_state = None
            self._first_pose = None
            self._first_tech_state = None
            if isinstance(state, (list, tuple)) and len(state) >= 6:
                self._prev_tech_state = list(state[:6])
                self._first_tech_state = list(state[:6])
            current_pose = self.get_pose_data()
            if current_pose is not None and len(current_pose) >= 6:
                self._first_pose = list(current_pose[:6])
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()

    def stop_control(self):
        if not self.is_controlling:
            return
        self.is_controlling = False
        self.control_thread_running = False
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=1.0)
        with self._control_lock:
            self.pose_queue.clear()
            self.end_effector_queue.clear()
            self._target_pose = None
            self._target_end_effector = None
            self._prev_tech_state = None
            self._first_pose = None
            self._first_tech_state = None

    def _control_loop(self):
        """控制循环：应用最新的 pose/joint/末端指令到仿真"""
        while self.control_thread_running and self.model and self.data:
            with self._control_lock:
                if self.pose_queue:
                    self._target_pose = self.pose_queue[-1]
                if self.end_effector_queue:
                    self._target_end_effector = self.end_effector_queue[-1]

            if self._target_pose is not None:
                resolved_pose = self._resolve_control_pose(self._target_pose)
                if resolved_pose is not None:
                    self._apply_pose_command(resolved_pose)

            if self._target_end_effector is not None:
                self._apply_end_effector_command(self._target_end_effector)

            time.sleep(self.min_interval if self.min_interval > 0 else 0.01)

    def add_pose_data(self, pose_data):
        with self._control_lock:
            if self.is_controlling:
                self.pose_queue.append(pose_data)

    def add_end_effector_data(self, end_effector_data):
        with self._control_lock:
            if self.is_controlling:
                self.end_effector_queue.append(end_effector_data)

    def _apply_pose_command(self, target_pose):
        if self.model is None or self.data is None or self.mujoco is None:
            return

        with self._control_lock:
            if len(target_pose) == self.model.nq:
                self.data.qpos[: self.model.nq] = np.array(target_pose[: self.model.nq], dtype=float)
                self.data.qvel[:] = 0
                self.mj_forward(self.model, self.data)
                return

            if len(target_pose) < 6:
                return

            target_pos = np.array(target_pose[:3], dtype=float)
            target_mat = self._rpy_to_matrix(*target_pose[3:6])

            current_pose, current_mat = self._get_end_effector_pose(return_mat=True, lock_already_held=True)
            if current_pose is None or current_mat is None:
                return

            pos_err = target_pos - np.array(current_pose[:3])
            rot_err = self._rotation_error(current_mat, target_mat)
            err = np.concatenate((pos_err, rot_err))

            jac_pos = np.zeros((3, self.model.nv))
            jac_rot = np.zeros((3, self.model.nv))
            if self._ee_site_id is not None:
                self.mujoco.mj_jacSite(self.model, self.data, jac_pos, jac_rot, self._ee_site_id)
            else:
                body_id = self._ee_body_id if self._ee_body_id is not None else self.model.nbody - 1
                self.mujoco.mj_jacBody(self.model, self.data, jac_pos, jac_rot, body_id)
            jac = np.vstack((jac_pos, jac_rot))[:, : self._controlled_dofs]

            if jac.size == 0:
                return

            # 阻尼最小二乘求解关节增量
            lam = 1e-3
            jjt = jac @ jac.T + lam * np.eye(6)
            dq = jac.T @ np.linalg.solve(jjt, err)
            dq = np.clip(dq, -0.05, 0.05)

            self.data.qpos[: self._controlled_dofs] += dq
            self.data.qvel[:] = 0
            self.mj_forward(self.model, self.data)

    def _resolve_control_pose(self, pose_data):
        if pose_data is None:
            return None
        if not isinstance(pose_data, (list, tuple)) or len(pose_data) < 6:
            return pose_data

        tech_state = list(pose_data[:6])
        if self.control_mode == 2:
            return tech_state

        if self._prev_tech_state is None or self._first_pose is None:
            current_pose = self.get_pose_data()
            if current_pose is None or len(current_pose) < 6:
                return None
            self._prev_tech_state = tech_state
            self._first_pose = list(current_pose[:6])
            if self._first_tech_state is None:
                self._first_tech_state = tech_state
            return None

        if self._first_tech_state is None:
            self._first_tech_state = self._prev_tech_state

        delta = [tech_state[i] - self._first_tech_state[i] for i in range(6)]
        if self.control_mode == 0:
            next_pose = [self._first_pose[i] + delta[i] for i in range(6)]
        elif self.control_mode == 1:
            next_pose = [
                self._first_pose[0] + delta[0],
                self._first_pose[1] + delta[1],
                self._first_pose[2] + delta[2],
                tech_state[3],
                tech_state[4],
                tech_state[5],
            ]
        else:
            next_pose = tech_state

        self._prev_tech_state = tech_state
        return next_pose

    def _apply_end_effector_command(self, ee_cmd):
        if self.model is None or self.data is None or self.model.nu == 0:
            return

        with self._control_lock:
            try:
                val = float(ee_cmd[0]) if isinstance(ee_cmd, (list, tuple)) else float(ee_cmd)
                self.data.ctrl[0] = val
            except Exception:
                self.data.ctrl[0] = 0.0

    def _resolve_end_effector_refs(self) -> Tuple[Optional[int], Optional[int]]:
        """根据配置/模型推断末端 site 与 body"""
        if self.model is None or self.mujoco is None:
            return None, None

        site_id: Optional[int] = None
        if self.model.nsite > 0:
            if self.end_effector_site:
                try:
                    site_id = self.mujoco.mj_name2id(
                        self.model, self.mujoco.mjtObj.mjOBJ_SITE, self.end_effector_site
                    )
                except Exception:
                    site_id = None
            if site_id is None:
                site_id = self.model.nsite - 1

        body_id: Optional[int] = None
        if site_id is not None:
            body_id = int(self.model.site_bodyid[site_id])
        elif self.model.nbody > 0:
            body_id = self.model.nbody - 1

        return site_id, body_id

    def _load_mujoco_model(self, package_path: str, urdf_path: str):
        package_dir = self._normalize_package_dir(Path(package_path))
        path = self._resolve_urdf_path(package_dir, urdf_path)
        if path.suffix.lower() != ".urdf":
            return self.mujoco.MjModel.from_xml_path(str(path))

        fixed_xml = self._build_urdf_xml(package_dir, path)
        meshes_dir = (package_dir / "meshes").resolve()
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".mujoco.urdf",
                delete=False,
                dir=str(meshes_dir if meshes_dir.is_dir() else package_dir),
            ) as tmp:
                tmp.write(fixed_xml)
                temp_path = tmp.name
            return self.mujoco.MjModel.from_xml_path(temp_path)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def _build_urdf_xml(self, package_dir: Path, path: Path) -> bytes:
        urdf_text = path.read_text(encoding="utf-8")
        root = ET.fromstring(urdf_text)

        urdf_dir = path.parent.resolve()
        meshes_dir = (package_dir / "meshes").resolve()

        for mesh in root.iter("mesh"):
            filename = mesh.get("filename")
            if not filename:
                continue

            final_path = None
            if filename.startswith("package://"):
                rel = filename.replace("package://", "", 1)
                parts = Path(rel).parts
                if parts and parts[0] == package_dir.name:
                    rel = Path(*parts[1:]) if len(parts) > 1 else Path()
                rel_path = Path(rel)
                if rel_path.parts and rel_path.parts[0] == "meshes":
                    rel_path = Path(*rel_path.parts[1:])
                final_path = meshes_dir / rel_path
            else:
                candidate = Path(filename)
                if candidate.is_absolute():
                    final_path = candidate
                elif candidate.name == filename:
                    final_path = meshes_dir / candidate.name
                else:
                    final_path = (urdf_dir / candidate).resolve()

            if final_path is not None:
                mesh.set("filename", str(final_path.resolve()))

        return ET.tostring(root, encoding="utf-8")

    def _to_package_relative(self, package_dir: Path, asset_path: Path) -> str:
        resolved = asset_path.resolve()
        try:
            rel = resolved.relative_to(package_dir.resolve())
            return str((package_dir / rel).resolve())
        except ValueError:
            return str(resolved)

    def _normalize_package_dir(self, package_dir: Path) -> Path:
        if package_dir.is_file():
            package_dir = package_dir.parent
        if package_dir.name == "urdf" and (package_dir.parent / "meshes").is_dir():
            return package_dir.parent.resolve()
        return package_dir.resolve()

    def _resolve_urdf_path(self, package_dir: Path, urdf_path: str) -> Path:
        if urdf_path:
            candidate = (package_dir / urdf_path).resolve()
            if candidate.exists():
                return candidate
            raise FileNotFoundError(f"URDF 文件不存在: {candidate}")

        urdf_dir = package_dir / "urdf"
        if urdf_dir.is_dir():
            urdf_files = sorted(urdf_dir.glob("*.urdf"))
            if urdf_files:
                return urdf_files[0].resolve()

        raise FileNotFoundError(f"未在包目录中找到 URDF: {package_dir}")
