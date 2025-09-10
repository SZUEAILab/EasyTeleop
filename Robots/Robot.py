class Robot:
    """
    机器人控制基类，所有具体机器人控制器需继承并实现以下方法。

    方法说明：
    - __init__(self, ip): 初始化机器人，参数为IP地址。
    - start_control(self, state, trigger=None): 启动控制，state为位姿信息（长度6为xyz+欧拉角，长度7为xyz+四元数），trigger为夹爪开合度（0~1），可选。
    - stop_control(self): 停止控制。
    - get_state(self): 获取当前位姿（位置+姿态，返回格式由子类定义）。
    - get_gripper(self): 获取当前夹爪状态（返回格式由子类定义）。
    """
    def __init__(self, config):
        self.config = config
        self._state = None
        self._gripper = None
        self._on_state = None  # 新增回调接口

    def on_state(self, callback):
        """设置状态更新回调函数"""
        self._on_state = callback

    def start(self):
        """
        启动某些线程或初始化操作。
        """
        raise NotImplementedError("start方法需由子类实现")

    def start_control(self, state, trigger=None):
        """
        启动机器人控制。
        :param state: 位姿信息，长度为6（xyz+欧拉角）或7（xyz+四元数）。
        :param trigger: 夹爪开合度，0~1，默认为None表示不控制夹爪。
        """
        raise NotImplementedError("start_control方法需由子类实现")

    def stop_control(self):
        """
        停止机器人控制。
        """
        raise NotImplementedError("stop_control方法需由子类实现")

    def get_state(self):
        """
        获取机器人当前位置和姿态。
        :return: 位置+姿态（格式由子类定义）
        """
        raise NotImplementedError("get_state方法需由子类实现")

    def get_gripper(self):
        """
        获取夹爪状态。
        :return: 夹爪状态（格式由子类定义）
        """
        raise NotImplementedError("get_gripper方法需由子类实现")