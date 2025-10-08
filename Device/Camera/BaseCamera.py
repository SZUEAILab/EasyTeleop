import numpy as np
import logging
from typing import Dict, Any, Tuple
from ..BaseDevice import BaseDevice
from abc import abstractmethod


# # 定义摄像头接口，方便获取图片帧和信息
class BaseCamera(BaseDevice):
    """摄像头接口抽象类"""
    def __init__(self,config: str):
        super().__init__(config)
        self._events.update({
            "frame": self._default_callback,# rgb图像
        })

    @abstractmethod
    def get_frames(self) -> np.ndarray:
        """获取图片帧"""
        pass