import numpy as np
from typing import Dict, Any, Tuple, Callable
from abc import ABC, abstractmethod


class BaseDevice(ABC):
    """设备接口抽象类，定义设备的基本操作和状态管理"""
    
    def __init__(self, config: Dict[str, Any] = None):
        # 配置信息
        self.config = config or {}
        # 需要的配置字段（由子类定义，格式: {字段名: 类型/描述}）
        self.need_config: Dict[str, Any] = {}
        # 回调函数字典
        self._events: Dict[str, Callable] = {}
        # 连接状态: 0=未连接(灰色), 1=已连接(绿色), 2=断开连接,需要实现重连机制(红色)
        self._conn_status: int = 0

    def on(self, event_name: str, callback: Callable) -> bool:
        """
        注册事件回调函数
        :param event_name: 事件名称
        :param callback: 回调函数
        """
        if not callable(callback):
            raise ValueError("回调函数必须是可调用对象")
            
        # 如果事件存在则更新回调
        if event_name in self._events:
            self._events[event_name] = callback
            return True
        
        return False

    def off(self, event_name: str) -> bool:
        """
        移除事件回调函数，恢复默认回调
        :param event_name: 事件名称
        """
        if event_name in self._events:
            self._events[event_name] = self._default_callback
            return True
        
        return False

    def emit(self, event_name: str, *args, **kwargs) -> None:
        """
        触发事件，执行注册的回调函数
        :param event_name: 事件名称
        :param args: 位置参数
        :param kwargs: 关键字参数
        """
        if event_name in self._events:
            try:
                self._events[event_name](*args, **kwargs)
            except Exception as e:
                self.emit("error_occurred", f"事件{event_name}执行失败: {str(e)}")

    def _default_callback(self, *args, **kwargs) -> None:
        """默认回调函数，什么也不做"""
        pass

    def get_conn_status(self) -> int:
        """
        获取设备连接状态
        :return: 0=未连接, 1=已连接, 2=断开连接
        """
        return self._conn_status

    def set_conn_status(self, status: int) -> None:
        """
        设置设备连接状态，并触发状态变化事件
        :param status: 0=未连接, 1=已连接, 2=断开连接
        """
        if status in (0, 1, 2) and status != self._conn_status:
            self._conn_status = status
            
    @abstractmethod
    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        设置设备配置，需验证配置是否符合need_config要求
        :param config: 配置字典
        :return: 是否设置成功
        """
        pass

    @abstractmethod
    def start(self) -> bool:
        """
        启动设备
        :return: 是否启动成功
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """
        停止设备
        :return: 是否停止成功
        """
        pass

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证配置是否满足需求
        :param config: 待验证的配置
        :return: (是否有效, 错误信息)
        """
        for key in self.need_config:
            if key not in config:
                return False, f"缺少必要配置项: {key}"
            # 检查类型（如果定义了类型要求）
            required_type = self.need_config[key]
            if required_type is not None and not isinstance(config[key], required_type):
                return False, f"配置项{key}类型错误，需要{required_type}，实际是{type(config[key])}"
            
        return True, "配置有效"