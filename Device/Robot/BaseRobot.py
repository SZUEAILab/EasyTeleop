from ..BaseDevice import BaseDevice
from typing import Dict, Any
from abc import abstractmethod
from queue import Queue
class BaseRobot(BaseDevice):
    """
    机器人控制基类，所有具体机器人控制器需继承并实现以下方法。

    方法说明：
    - 
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # 创建两个队列，分别用于位姿和夹爪控制
        self.pose_queue = Queue()
        self.gripper_queue = Queue()

    @abstractmethod
    def add_pose_data(self, pose_data) -> None:
        """
        添加机器人位姿数据
        :param pose_data: 位姿数据
        :return: None
        """
        pass
    @abstractmethod
    def add_gripper_data(self, gripper_data) -> None:
        """
        添加机器人夹爪数据
        :param gripper_data: 夹爪数据
        :return: None
        """

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