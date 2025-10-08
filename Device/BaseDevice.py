import numpy as np
from typing import Dict, Any, Tuple, Callable
from abc import ABC, abstractmethod
import asyncio
import threading
import time


class BaseDevice(ABC):
    """设备接口抽象类，定义设备的基本操作和状态管理"""
    name: str = "Base Device"
    description: str = "Base device description"
    # 需要的配置字段（由子类定义，格式: {字段名: 类型/描述}）
    need_config: Dict[str, Any] = {}

    @classmethod
    def get_need_config(cls) -> Dict[str, Any]:
        """
        获取当前设备所需配置字段
        :return: 配置字段字典
        """
        return cls.need_config
    
    @classmethod
    def get_type_info(cls) -> Dict[str, Any]:
        """
        获取设备类型信息
        :return: 包含名称、描述和配置需求的字典
        """
        return {
            "name": cls.name,
            "description": cls.description,
            "need_config": cls.need_config
        }
    
    def __init__(self, config: Dict[str, Any] = None):
        # 配置信息
        self.config = None
        # 如果提供了配置，则设置配置
        if config:
            self.set_config(config)
        
        # 回调函数字典
        self._events: Dict[str, Callable] = {
            "status_change": self._default_callback,
            "error": self._default_error_callback,
        }
        # 连接状态: 0=未连接(灰色), 1=已连接(绿色), 2=断开连接,需要实现重连机制(红色)
        self._conn_status: int = 0
        # 重连(state 2 -> state 1的尝试)间隔秒数
        self.reconnect_interval = 1
        # 设备主循环线程
        self._main_loop_thread = None

    def on(self, event_name: str, callback: Callable = None) -> Callable:
        """
        注册事件回调函数 - 可作为装饰器或普通方法使用
        :param event_name: 事件名称
        :param callback: 回调函数（可选，当作为装饰器使用时不需要）
        :return: 装饰器函数或注册结果
        """
        # 装饰器工厂模式
        def decorator(func):
            if not callable(func):
                raise ValueError("回调函数必须是可调用对象")
                
            # 如果事件存在则更新回调
            if event_name in self._events:
                self._events[event_name] = func
            else:
                # 如果事件不存在，添加新的事件处理器
                self._events[event_name] = func
            return func
        
        # 如果提供了callback参数，则按照原来的方式工作
        if callback is not None:
            return decorator(callback)
        
        # 否则返回装饰器
        return decorator

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
        事件处理应是非阻塞的，对于耗时操作应该在独立线程中执行
        :param event_name: 事件名称
        :param args: 位置参数
        :param kwargs: 关键字参数
        """
        if event_name in self._events:
            try:
                # self._events[event_name](*args, **kwargs)
                # 异步执行回调函数以避免阻塞事件循环
                callback = self._events[event_name]
                if asyncio.iscoroutinefunction(callback):
                    # 如果是异步函数，在新事件循环中运行
                    thread = threading.Thread(target=self._run_async_callback, args=(callback, args, kwargs), daemon=True)
                    thread.start()
                else:
                    # 同步函数在新线程中运行以避免阻塞
                    thread = threading.Thread(target=callback, args=args, kwargs=kwargs, daemon=True)
                    thread.start()
            except Exception as e:
                self.emit("error", f"事件{event_name}执行失败: {str(e)}")

    def _run_async_callback(self, callback, args, kwargs):
        """运行异步回调函数"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(callback(*args, **kwargs))
            loop.close()
        except Exception as e:
            self.emit("error", f"异步事件回调执行失败: {str(e)}")

    def _default_callback(self, *args, **kwargs) -> None:
        """默认回调函数，什么也不做"""
        pass
    def _default_error_callback(self, error_msg: str) -> None:
        """默认错误回调函数，打印错误信息"""
        print(f"设备{self.__class__.__name__}发生错误: {error_msg}")

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
            old_status = self._conn_status
            self._conn_status = status
            
            # 触发状态变化事件
            self.emit("status_change", {
                "old_status": old_status,
                "new_status": status,
            })
        
    

    def _main_loop(self):
        """
        设备主循环,不需要重写,依据_conn_status自动处理连接和运行_main逻辑
        """
        while self._conn_status != 0:  # 只要不是未连接状态就继续运行
            if self.get_conn_status() == 1:
                try:
                    self._main()
                except Exception as e:
                    self.set_conn_status(2)
                    self.emit("error", f"设备{self.__class__.__name__}运行失败: {str(e)}")
            elif self.get_conn_status() == 2:
                try:
                    if self._connect_device():
                        self.set_conn_status(1) 
                        continue
                except Exception as e:
                    self.emit("error", f"设备{self.__class__.__name__}重连失败: {str(e)}")
                time.sleep(self.reconnect_interval)



    def start(self) -> bool:
        """
        启动设备，包括启动主循环和设置初始状态
        :return: False已经启动，True启动成功
        """
        if self._conn_status != 0:
            return False  # 设备已经在运行中
        
        self.set_conn_status(2)#设置为2会首先尝试连接，复用重连逻辑
        self._main_loop_thread = threading.Thread(target=self._main_loop, daemon=True)
        self._main_loop_thread.start()
        return True
    

    def stop(self) -> bool:
        """
        停止设备
        :return: 是否停止成功
        """
        # 设置状态为未连接，这会停止主循环和重连循环
        self.set_conn_status(0)
        
        # 等待线程结束
        if self._main_loop_thread and self._main_loop_thread.is_alive():
            self._main_loop_thread.join(timeout=2.0)  # 等待最多2秒
        
        try:
            disconnected = self._disconnect_device()
            return disconnected
        except Exception as e:
            self.emit("error", f"设备停止失败: {str(e)}")
            return False
    @abstractmethod
    def _main(self):
        """
        设备主逻辑，在独立线程中运行
        子类应实现具体的设备逻辑
        """
        pass
    @abstractmethod
    def _connect_device(self) -> bool:
        """
        连接设备的具体实现
        子类应重写此方法实现具体的连接逻辑
        :return: 是否连接成功
        """
        # 默认实现，子类应覆盖
        return True    
    @abstractmethod
    def _disconnect_device(self) -> bool:
        """
        断开设备连接的具体实现
        子类应重写此方法实现具体的断开连接逻辑
        :return: 是否断开连接成功
        """
        # 默认实现，子类应覆盖
        return True
    @abstractmethod
    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        设置设备配置，需验证配置是否符合need_config要求
        :param config: 配置字典
        :return: 是否设置成功
        """
        # 检查必需的配置字段
        for key in self.need_config:
            if key not in config:
                raise ValueError(f"缺少必需的配置字段: {key}")
        
        self.config = config
        return True