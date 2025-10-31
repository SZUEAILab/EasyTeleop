from .BaseRobot import BaseRobot
import threading
import time
import math
import copy

class TestRobot(BaseRobot):
    name = "测试机器人"
    description = "提供start_control和stop_control方法的测试机器人,同时周期性生成模拟的机器人状态数据，触发state事件"
    need_config = {
        "fps": {
            "description": "状态更新帧率",
            "type": "int",
            "default": 30
        }
    }
    
    def __init__(self, config=None):
        super().__init__(config)
        self.fps = 30  # 默认帧率
        self._time_counter = 0
        self._control_active = False
        self._control_lock = threading.Lock()
        
        # 模拟的机器人初始状态
        self._robot_state = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # 6个关节角度
        self._cartesian_position = [0.3, 0.0, 0.5]  # XYZ坐标
        self._cartesian_orientation = [0.0, 0.0, 0.0]  # RPY欧拉角
        self._gripper_state = 0.0  # 夹爪状态 0.0-1.0
        
        # 控制相关变量
        self._arm_first_state = None
        self._prev_tech_state = None

    def add_pose_data(self, pose_data):
        pass
    
    def add_end_effector_data(self, end_effector_data):
        pass

    def set_config(self, config):
        """设置设备配置"""
        super().set_config(config)
        if "fps" in config:
            self.fps = config["fps"]
            self.min_interval = 1.0 / self.fps if self.fps > 0 else 0
        return True

    def _connect_device(self) -> bool:
        """连接设备"""
        return True

    def _disconnect_device(self) -> bool:
        """断开设备连接"""
        # 停止控制（如果正在控制中）
        self.stop_control()
        return True

    def _main(self):
        last_time = time.time()
        """设备主逻辑 - 每一帧执行一次"""
        self._time_counter += 1
        
        # 生成模拟的机器人状态数据
        # 模拟随时间变化的关节角度和位置
        t = self._time_counter / self.fps if self.fps > 0 else self._time_counter * 0.1
        
        # 更新机器人状态
        self._robot_state = [
            math.sin(t * 0.5),
            math.cos(t * 0.5),
            math.sin(t * 0.8),
            math.cos(t * 0.8),
            math.sin(t * 1.2),
            math.cos(t * 1.2)
        ]
        
        self._cartesian_position = [
            0.3 + 0.1 * math.sin(t * 0.3),
            0.0 + 0.1 * math.cos(t * 0.3),
            0.5 + 0.05 * math.sin(t * 0.2)
        ]
        
        self._cartesian_orientation = [
            0.0 + 0.2 * math.sin(t * 0.5),
            0.0 + 0.1 * math.cos(t * 0.5),
            0.0 + 0.15 * math.sin(t * 0.3)
        ]
        
        self._gripper_state = (math.sin(t * 2) + 1) / 2  # 归一化到0-1之间
        
        # 触发state事件
        self.emit("state", self._robot_state)

        if self.fps > 0:
            # 帧率控制，而不是固定间隔
            current_time = time.time()
            elapsed = current_time - last_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)

    def start_control(self):
        """开始控制机器人"""
        pass

    def stop_control(self):
        """停止控制机器人"""
        pass

    def _control_loop(self):
        pass