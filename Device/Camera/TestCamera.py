from .BaseCamera import BaseCamera
import numpy as np
import threading
import time

class TestCamera(BaseCamera):
    description = "测试摄像头"
    name = "测试摄像头"
    need_config = {
        "fps": {
            "description": "帧率",
            "type": "int"
        }
    }

    def __init__(self, config=None):
        self._pulse_state = False  # 用于生成脉冲图片
        super().__init__(config)

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
        return True

    def _main(self):
        try:
            last_time = time.time()
            # 生成1080p黑白脉冲图片
            frame = self.get_frames()
            
            # 触发frame事件
            self.emit("frame", frame)
            
            # 只有当target_fps > 0时才进行帧率控制
            if self.fps > 0:
                # 帧率控制，而不是固定间隔
                current_time = time.time()
                elapsed = current_time - last_time
                if elapsed < self.min_interval:
                    time.sleep(self.min_interval - elapsed)
        except Exception as e:
            self.emit("error", str(e))
    def get_frames(self) -> np.ndarray:
        """获取一帧图片"""
        self._pulse_state = not self._pulse_state
        color = 255 if self._pulse_state else 0
        frame = np.full((720, 1080, 3), color, dtype=np.uint8)
        return frame