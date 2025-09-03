import numpy as np
import logging
from typing import Dict, Any, Tuple
from abc import ABC, abstractmethod


# # 定义摄像头接口，方便获取图片帧和信息
class BaseCamera(ABC):
    """摄像头接口抽象类"""
    def __init__(self, camera_type: str, camera_position:str, camera_serial: str):
        # 属性：设备名称，设备位置，序列号
        self.camera_type = camera_type
        self.camera_position = camera_position
        self.camera_serial = camera_serial
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{self.camera_position}")
        pass

    def logger_msg(self,msg:str):
        print(f"[{self.camera_type}][{self.camera_position}] {msg}")

    @abstractmethod
    def connect(self) -> bool:
        """连接摄像头"""
        pass
    @abstractmethod
    def disconnect(self) -> bool:
        """断开摄像头连接"""
        pass
    @abstractmethod
    def is_connected(self) -> bool:
        """检查摄像头是否连接"""
        pass
    @abstractmethod
    def get_frames(self) -> np.ndarray:
        """获取图片帧"""
        pass
    
    @abstractmethod
    def get_device_info(self) -> Dict[str, Any]:
        """获取摄像头信息"""
        pass

    @abstractmethod
    def get_frames(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取图片帧和深度帧"""
        pass