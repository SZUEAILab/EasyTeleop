from .BaseRobot import BaseRobot
import threading
import time
import math


class TestRobot(BaseRobot):
    """
    测试机械臂：
    - 提供 start_control / stop_control
    - 按设定帧率生成模拟 pose/joint/end_effector 数据并触发事件
    - 支持接收遥操作下发的姿态/末端指令并应用到模拟状态
    """

    name = "测试机械臂"
    description = "周期生成模拟状态并触发 pose/joint/end_effector 事件的测试机械臂"
    need_config = {
        "fps": {
            "description": "状态更新帧率",
            "type": "int",
            "default": 30,
        },
        "dof": {
            "description": "关节自由度数量",
            "type": "int",
            "default": 7,
        },
    }

    def __init__(self, config=None):
        super().__init__(config)
        self.fps = 30
        self.dof = 7
        self.min_interval = 1.0 / self.fps if self.fps > 0 else 0.1
        self._time_counter = 0

        # 状态缓存
        self._joints = [0.0] * self.dof
        self._cartesian_position = [0.35, 0.0, 0.45]
        self._cartesian_orientation = [0.0, 0.0, 0.0]
        self._gripper_state = 0.0

        # 控制线程
        self._control_thread = None
        self._control_thread_running = False
        self._control_lock = threading.Lock()

    def set_config(self, config):
        super().set_config(config)
        if "fps" in config:
            self.fps = config["fps"]
        if "dof" in config:
            self.dof = int(config["dof"])
        self._joints = [0.0] * self.dof
        self.min_interval = 1.0 / self.fps if self.fps > 0 else 0.1
        return True

    def _connect_device(self) -> bool:
        return True

    def _disconnect_device(self) -> bool:
        self.stop_control()
        return True

    def add_pose_data(self, pose_data):
        with self._control_lock:
            if self.is_controlling:
                self.pose_queue.append(pose_data)

    def add_end_effector_data(self, end_effector_data):
        with self._control_lock:
            if self.is_controlling:
                self.end_effector_queue.append(end_effector_data)

    def _main(self):
        """
        主循环：生成模拟状态并触发事件
        """
        last_time = time.time()
        self._time_counter += 1
        t = self._time_counter / self.fps if self.fps > 0 else self._time_counter * 0.1

        # 生成 joints（按 DOF 数量）
        self._joints = [
            math.sin(t * (0.3 + 0.1 * i)) * 90 for i in range(self.dof)
        ]

        # 生成 pose（XYZ + RPY）
        self._cartesian_position = [
            0.35 + 0.05 * math.sin(t * 0.3),
            0.0 + 0.08 * math.cos(t * 0.3),
            0.45 + 0.04 * math.sin(t * 0.2),
        ]
        self._cartesian_orientation = [
            0.2 * math.sin(t * 0.5),
            0.1 * math.cos(t * 0.5),
            0.15 * math.sin(t * 0.3),
        ]

        # 生成 end_effector（模拟 0-1000 范围）
        self._gripper_state = (math.sin(t * 2) + 1) / 2

        # 触发事件
        pose_payload = self._cartesian_position + self._cartesian_orientation
        self.emit("pose", pose_payload)
        self.emit("joint", self._joints)
        self.emit("end_effector", [self._gripper_state * 1000.0])

        # 帧率控制
        if self.fps > 0:
            elapsed = time.time() - last_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)

    def start_control(self, state=None, trigger=None):
        """开始控制，启动控制线程以应用遥操作输入"""
        if self.is_controlling:
            return
        self.is_controlling = True
        self._control_thread_running = True
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self._control_thread.start()

    def stop_control(self):
        """停止控制"""
        if not self.is_controlling:
            return
        self.is_controlling = False
        self._control_thread_running = False
        if self._control_thread and self._control_thread.is_alive():
            self._control_thread.join(timeout=1.0)
        self.pose_queue.clear()
        self.end_effector_queue.clear()

    def _control_loop(self):
        """
        控制线程：应用最新的遥操作指令到模拟状态
        """
        while self._control_thread_running:
            pose_data = None
            if self.pose_queue:
                pose_data = self.pose_queue[-1]
            if pose_data and len(pose_data) >= 6:
                with self._control_lock:
                    self._cartesian_position = pose_data[:3]
                    self._cartesian_orientation = pose_data[3:6]

            ee_data = None
            if self.end_effector_queue:
                ee_data = self.end_effector_queue[-1]
            if ee_data is not None:
                try:
                    if isinstance(ee_data, (list, tuple)):
                        self._gripper_state = float(ee_data[0]) / 1000.0
                    else:
                        self._gripper_state = float(ee_data)
                except Exception:
                    self._gripper_state = 0.0

            time.sleep(self.min_interval if self.min_interval > 0 else 0.05)
