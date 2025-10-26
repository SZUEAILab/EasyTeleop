from ..BaseDevice import BaseDevice
from typing import Dict, Any
from abc import abstractmethod
from collections import deque

class BaseRobot(BaseDevice):
    """
    机器人控制基类，所有具体机器人控制器需继承并实现以下方法。

    方法说明：
    - 
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

        self._events.update({
            "state": self._default_callback,
        })

        # 创建目标姿态队列，使用deque确保只保留最新数据
        self.pose_queue = deque(maxlen=10)
        self.end_effector_queue = deque(maxlen=10)

        # 控制线程
        self.is_controlling = False
        self.control_thread = None
        self.control_thread_running = False


    def add_pose_data(self, pose_data:list) -> None:
        """
        添加机器人位姿数据
        :param pose_data: 位姿数据
        :return: None
        """
        if self.is_controlling:
            self.pose_queue.append(pose_data)

    def add_end_effector_data(self, end_effector_data:list) -> None:
        """
        添加机器人末端执行器数据
        :param end_effector_data: 夹爪数据
        :return: None
        """
        if self.is_controlling:
            self.end_effector_queue.append(end_effector_data)

    @abstractmethod
    def start_control(self) -> None:
        """
        开始控制机器人
        :return: None
        """
        pass

    @abstractmethod
    def stop_control(self) -> None:
        """
        停止控制机器人
        :return: None
        """
        pass
