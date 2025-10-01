from abc import ABC, abstractmethod
from typing import Dict, Any, List
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