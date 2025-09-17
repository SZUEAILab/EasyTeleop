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


    @abstractmethod
    def connect(self) -> bool:
        """连接摄像头"""
        pass
    @abstractmethod
    def disconnect(self) -> bool:
        """断开摄像头连接"""
        pass
    @abstractmethod
    def get_frames(self) -> np.ndarray:
        """获取图片帧"""
        pass

    @abstractmethod
    def get_frames(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取图片帧和深度帧"""
        pass