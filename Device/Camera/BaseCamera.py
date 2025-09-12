import numpy as np
import logging
from typing import Dict, Any, Tuple
from abc import ABC, abstractmethod


# # 定义摄像头接口，方便获取图片帧和信息
class BaseCamera(ABC):
    """摄像头接口抽象类"""
    def __init__(self,config: str):
        # 属性：设备名称，设备位置，序列号
        self.config = config
        self._events = {}
        # 连接状态: 0=未连接(灰色), 1=已连接(绿色), 2=断开连接(红色)
        self._conn_status = 0
        
    def on(self, event_name: str, callback):
        """注册事件回调函数"""
        # 如果事件不存在
        if event_name not in self._events:
            return
        # 将回调函数添加到事件列表中
        self._events[event_name] = callback

    def off(self, event_name: str):
        """移除事件回调函数"""
        if event_name not in self._events:
            return
        self._events[event_name] = self._default_callback

    def emit(self, event_name: str, *args, **kwargs):
        """触发事件，执行所有注册的回调函数"""
        if event_name not in self._events:
            return
        self._events[event_name](*args, **kwargs)
        
    def _default_callback(self,*args, **kwargs):
        pass

    def get_conn_status(self):
        """
        获取设备连接状态
        :return: 0=未连接(灰色), 1=已连接(绿色), 2=断开连接(红色)
        """
        return self._conn_status

    def set_conn_status(self, status):
        """
        设置设备连接状态
        :param status: 0=未连接, 1=已连接, 2=断开连接
        """
        if status in (0, 1, 2):
            self._conn_status = status


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