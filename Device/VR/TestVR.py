from .BaseVR import BaseVR
import json
import threading
import time
import math

class TestVR(BaseVR):
    name = "测试VR设备"
    description = "测试VR设备"
    need_config = {
        "fps": {
            "description": "帧率",
            "type": "int"
        }
    }

    def __init__(self, config=None):
        super().__init__(config)
        self.fps = 30  # 默认帧率
        self._time_counter = 0

    def set_config(self, config):
        """设置设备配置"""
        super().set_config(config)
        if "fps" in config:
            self.fps = config["fps"]
        return True

    def _connect_device(self) -> bool:
        """连接设备"""
        return True

    def _disconnect_device(self) -> bool:
        """断开设备连接"""
        return True

    def _main(self):
        """设备主逻辑"""
        self._data_generation_active = True
        self._stop_data_event.clear()
        
        interval = 1.0 / self.fps if self.fps > 0 else 0.1
        last_time = time.time()
        self._time_counter = 0
        
        while self.get_conn_status() == 1 and self._data_generation_active:
            self._time_counter += 1
            
            # 生成模拟的JSON数据包
            # 模拟随时间变化的位置和旋转数据
            t = self._time_counter * interval
            data = {
                "timestamp": time.time(),
                "hmd": {
                    "position": {
                        "x": math.sin(t),
                        "y": math.cos(t),
                        "z": math.sin(t) * math.cos(t)
                    },
                    "rotation": {
                        "x": math.sin(t * 0.5),
                        "y": math.cos(t * 0.5),
                        "z": math.sin(t * 0.3),
                        "w": math.cos(t * 0.3)
                    }
                },
                "left_controller": {
                    "position": {
                        "x": math.sin(t * 1.2),
                        "y": math.cos(t * 1.2) + 0.5,
                        "z": math.sin(t * 1.2) * math.cos(t * 1.2)
                    },
                    "rotation": {
                        "x": math.sin(t * 0.7),
                        "y": math.cos(t * 0.7),
                        "z": math.sin(t * 0.4),
                        "w": math.cos(t * 0.4)
                    },
                    "trigger": (math.sin(t * 2) + 1) / 2,  # 归一化到0-1之间
                    "grip": (math.cos(t * 2) + 1) / 2       # 归一化到0-1之间
                },
                "right_controller": {
                    "position": {
                        "x": math.sin(t * 1.5) + 0.2,
                        "y": math.cos(t * 1.5) + 0.5,
                        "z": math.sin(t * 1.5) * math.cos(t * 1.5)
                    },
                    "rotation": {
                        "x": math.sin(t * 0.9),
                        "y": math.cos(t * 0.9),
                        "z": math.sin(t * 0.6),
                        "w": math.cos(t * 0.6)
                    },
                    "trigger": (math.cos(t * 2) + 1) / 2,   # 归一化到0-1之间
                    "grip": (math.sin(t * 2) + 1) / 2       # 归一化到0-1之间
                }
            }
            
            # 触发message事件
            self.emit("message", json.dumps(data))
            
            # 等待下一帧
            time.sleep(interval)