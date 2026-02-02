from .BaseCamera import BaseCamera
import numpy as np
import threading
import time

class TestCamera(BaseCamera):
    description = "测试摄像头"
    name = "会以设定帧率生成1080p的黑白脉冲图像"
    need_config = {
        "fps": {
            "description": "帧率",
            "type": "int"
        }
    }

    def __init__(self, config=None):
        self._pulse_state = False  # 用于生成脉冲图片
        self._frame_index = 0
        self._grid = None
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
        """获取一帧图片?"""
        height, width = 720, 1080
        if self._grid is None:
            xs = np.linspace(0.0, 1.0, width, dtype=np.float32)
            ys = np.linspace(0.0, 1.0, height, dtype=np.float32)
            self._grid = np.meshgrid(xs, ys)

        x, y = self._grid
        t = self._frame_index / max(self.fps, 1)
        self._frame_index += 1

        # Moving gradient background.
        r = (np.sin(2.0 * np.pi * (x + t * 0.20)) + 1.0) * 0.5
        g = (np.sin(2.0 * np.pi * (y + t * 0.15)) + 1.0) * 0.5
        b = (np.sin(2.0 * np.pi * (x + y + t * 0.10)) + 1.0) * 0.5

        frame = np.stack([r, g, b], axis=-1)

        # Animated circle overlay.
        cx = 0.5 + 0.25 * np.sin(2.0 * np.pi * t * 0.40)
        cy = 0.5 + 0.20 * np.cos(2.0 * np.pi * t * 0.35)
        radius = 0.12 + 0.02 * np.sin(2.0 * np.pi * t * 0.90)
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        mask = dist < radius
        frame[mask] = np.array([1.0, 0.7, 0.2], dtype=np.float32)

        return (frame * 255.0).astype(np.uint8)
