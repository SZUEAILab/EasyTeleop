class Robot:
    """
    需要实现以下方法
    """
    def __init__(self, ip):
        self.ip = ip
    
    def start_control(self, state, trigger=None):
        """
        state:位姿信息,长度为6是xyz+欧拉角,长度为7则是4元数
        trigger:0~1的夹爪开合度,不填写则不控制夹爪
        """
        pass
    def stop_control(self):
        pass
    def get_state(self):
        """
        获取位置+姿态(欧拉角)
        """
        pass
    def get_gripper(self):
        pass