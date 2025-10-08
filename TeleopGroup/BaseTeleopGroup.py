from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable
import asyncio
import threading
import time
from Components import TeleopMiddleware
from Components import DataCollect


class BaseTeleopGroup(ABC):
    """遥操作组接口抽象类，定义遥操作组的基本属性和方法"""

    # 遥操组类型名称
    name: str = "Base Teleop Group"
    
    # 遥操组类型描述
    description: str = "Base teleoperation group type"
    
    # 遥操组所需配置字段（由子类定义）
    need_config: List[Dict[str, Any]] = []

    def __init__(self, devices = None):
        """
        初始化遥操组
        :param devices: 设备实例列表
        """
        self.teleop = TeleopMiddleware()
        self.data_collect = DataCollect()
        self.running = False
        
        # 设备引用
        self.devices = devices or []  # 存储所有设备实例
        
        # 回调函数字典
        self._events: Dict[str, Callable] = {
            "status_change": self._default_callback,
            "error": self._default_error_callback,
        }
        
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
        print(f"遥操组{self.__class__.__name__}发生错误: {error_msg}")

    @classmethod
    def get_type_info(cls) -> Dict[str, Any]:
        """
        获取遥操组类型信息
        :return: 包含名称、描述和配置需求的字典
        """
        return {
            "name": cls.name,
            "description": cls.description,
            "need_config": cls.need_config
        }

    @classmethod
    def get_type_name(cls) -> str:
        """
        获取遥操组类型名称，默认使用类名
        :return: 类型名称
        """
        return cls.__name__

    def get_status(self) -> Dict[str, Any]:
        """
        获取遥操组当前状态
        :return: 状态字典
        """
        return {
            "running": self.running,
            "collecting": self.data_collect.capture_state
        }
    @abstractmethod
    def start(self) -> bool:
        """
        启动遥操组
        :return: 是否启动成功
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """
        停止遥操组
        :return: 是否停止成功
        """
        pass