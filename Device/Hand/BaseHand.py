from ..BaseDevice import BaseDevice
from collections import deque
from abc import abstractmethod

class BaseHand(BaseDevice):
    def __init__(self, config):
        super().__init__(config)

        self._events.update({
            "state": self._default_callback,#机械手状态，List
        })

        # 使用deque作为hand_queue，设置maxlen为10，当超过长度时自动移除最旧的元素
        self.hand_queue = deque(maxlen=10)
        # 控制线程
        self.is_controlling = False
        self.control_thread = None
        self.control_thread_running = False

    def add_hand_data(self,hand_data):
        self.hand_queue.append(hand_data)

    @abstractmethod
    def start_control(self) -> None:
        """
        开始控制机器人
        :return: None
        """
        pass

    @abstractmethod
    def stop_control(self) -> None:
        pass

    @abstractmethod
    def _control_loop(self) -> None:
        pass