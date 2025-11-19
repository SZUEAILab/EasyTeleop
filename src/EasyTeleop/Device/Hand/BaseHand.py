import asyncio
from abc import ABC, abstractmethod

class BaseHand(ABC):
    """异步灵巧手控制基类"""
    name = "基础灵巧手"
    description = "灵巧手控制基类"
    need_config = {}

    def __init__(self, config):
        self.config = config
        self.is_connected = False
        self.event_listeners = {}  # 事件监听回调

    def on(self, event, callback):
        """注册事件监听"""
        if event not in self.event_listeners:
            self.event_listeners[event] = []
        self.event_listeners[event].append(callback)

    async def emit(self, event, data):
        """异步触发事件"""
        if event in self.event_listeners:
            # 并发执行所有回调
            await asyncio.gather(
                *[callback(data) for callback in self.event_listeners[event]]
            )

    @abstractmethod
    async def _connect_device(self) -> bool:
        """异步连接设备"""
        pass

    @abstractmethod
    async def _disconnect_device(self) -> bool:
        """异步断开连接"""
        pass

    @abstractmethod
    async def start_control(self) -> None:
        """启动异步控制任务"""
        pass

    @abstractmethod
    async def stop_control(self) -> None:
        """停止异步控制任务"""
        pass

    @abstractmethod
    async def handle_openxr(self, hand_data: dict) -> list:
        """处理OpenXR数据"""
        pass