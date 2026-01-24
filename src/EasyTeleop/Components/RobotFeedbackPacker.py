import threading
import time
from typing import Dict, Any, Optional, Callable


class RobotFeedbackPacker:
    """
    作用：
    - 接收异步到达的 pose / joints / end_effector
    - 为每个 arm_id 缓存最新状态，条件满足时组装为单个「Device」反馈包
    - 通过 packet 事件抛出给外层（例如 VR 设备）发送

    设计思路：
    - 状态缓存：以 arm_id 为键，存储最新 pose/joints/end_effector 及时间戳
    - 合包条件：pose 和 joints 必须同时可用；end_effector 可选
    - 解耦发送：组件只负责构包和事件发射，不直接依赖 VR/网络层
    - 当前组件未做时效过滤，默认用最新缓存

    典型使用：
    packer = RobotFeedbackPacker()
    packer.on("packet", vr_device.add_feedback_data)  # 绑定发送
    packer.add_feedback(robot, arm_id=0, pose=pose_data)
    packer.add_feedback(robot, arm_id=0, joints=joint_data)
    packer.add_feedback(robot, arm_id=0, end_effector=ee_data)
    """

    def __init__(self):
        self._events = {
            "packet": self._default_callback,
            "error": self._default_error_callback,
        }
        self._states: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def on(self, event_name: str, callback: Callable = None) -> Callable:
        """注册事件回调，支持装饰器用法"""
        def decorator(func):
            if not callable(func):
                raise ValueError("回调函数必须是可调用对象")
            if event_name in self._events:
                self._events[event_name] = func
            else:
                self._events[event_name] = func
            return func

        if callback is not None:
            return decorator(callback)
        return decorator

    def off(self, event_name: str) -> bool:
        if event_name in self._events:
            self._events[event_name] = self._default_callback
            return True
        return False

    def emit(self, event_name: str, *args, **kwargs) -> None:
        if event_name in self._events:
            try:
                cb = self._events[event_name]
                cb(*args, **kwargs)
            except Exception as e:
                if event_name != "error":
                    self.emit("error", f"事件{event_name}执行失败: {e}")

    def add_feedback(
        self,
        robot,
        arm_id: int,
        pose=None,
        joints=None,
        end_effector=None,
        ts: Optional[float] = None,
    ) -> None:
        """
        更新缓存并尝试生成反馈包:
        - pose 与 joints 缺一不发
        - end_effector 可选
        """
        if robot is None:
            return
        if ts is None:
            ts = time.time()

        with self._lock:
            state = self._states.setdefault(
                arm_id,
                {
                    "pose": None,
                    "joints": None,
                    "end_effector": None,
                    "pose_ts": None,
                    "joints_ts": None,
                    "ee_ts": None,
                },
            )
            if pose is not None:
                state["pose"] = pose
                state["pose_ts"] = ts
            if joints is not None:
                state["joints"] = joints
                state["joints_ts"] = ts
            if end_effector is not None:
                state["end_effector"] = end_effector
                state["ee_ts"] = ts

            snapshot = {
                "pose": state.get("pose"),
                "joints": state.get("joints"),
                "end_effector": state.get("end_effector"),
            }

        packet = self._build_packet(robot, arm_id, snapshot)
        if packet:
            self.emit("packet", packet)
            # 发包后清空该臂缓存，避免旧数据重复触发
            with self._lock:
                self._states[arm_id] = {
                    "pose": None,
                    "joints": None,
                    "end_effector": None,
                    "pose_ts": None,
                    "joints_ts": None,
                    "ee_ts": None,
                }

    def _build_packet(self, robot, arm_id: int, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pose_list = self._ensure_numeric_list(state.get("pose"))
        joints_list = self._ensure_numeric_list(state.get("joints"))
        end_effector_list = self._ensure_numeric_list(state.get("end_effector"), allow_none=True)

        if pose_list is None or joints_list is None:
            return None

        return {
            "type": "Device",
            "metadata": {
                "category": "Robot",
                "type": robot.__class__.__name__,
                "id": int(arm_id),
            },
            "payload": {
                "pose": pose_list,
                "end_effector": end_effector_list if end_effector_list is not None else [],
                "joints": joints_list,
            },
        }

    def _ensure_numeric_list(self, value, allow_none: bool = False) -> Optional[list]:
        if value is None:
            return None if not allow_none else None
        try:
            import numpy as np  # 延迟导入避免非必要依赖
        except Exception:
            np = None

        if isinstance(value, (list, tuple)):
            try:
                return [float(v) for v in value]
            except Exception:
                return None

        if np is not None and isinstance(value, np.ndarray):
            try:
                return [float(v) for v in value.flatten().tolist()]
            except Exception:
                return None
        return None

    def _default_callback(self, *args, **kwargs):
        pass

    def _default_error_callback(self, error_msg: str):
        print(f"[RobotFeedbackPacker Error]: {error_msg}")
