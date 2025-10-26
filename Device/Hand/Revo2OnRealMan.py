from .BaseHand import BaseHand
from Robotic_Arm.rm_robot_interface import rm_thread_mode_e,rm_peripheral_read_write_params_t, RoboticArm
import time
import threading

class Revo2OnRealMan(BaseHand):
    """RealMan通过Modbus驱动Revo2机械手"""

    name = "强脑科技Revo2机械手"
    description = "通过RealMan末端Modbus控制Revo2机械手"
    need_config = {
        "ip": {
            "type": "string",
            "description": "睿尔曼机械臂IP地址",
            "default": "192.168.1.18"
        },
        "port": {
            "type": "integer",
            "description": "睿尔曼机械臂端口号",
            "default": 8080
        },
        "baudrate":{
            "type": "int",
            "description": "Modbus串口波特率",
            "default": 460800
        },
        "address":{
            "type": "int",
            "description": "Revo2机械手Modbus设备地址,左手126，右手127",
            "default": 126
        },
    }
    
    def __init__(self, config):
        self.ip = None
        self.port = None
        self.baudrate = None
        self.address = None
        super().__init__(config)

        self.arm_controller = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)
        self.handle = None
        

    def set_config(self, config):
        """
        设置设备配置，验证配置是否符合need_config要求
        :param config: 配置字典
        :return: 是否设置成功
        """
        # 检查必需的配置字段
        for key in self.need_config:
            if key not in config:
                raise ValueError(f"缺少必需的配置字段: {key}")
        
        self.config = config
        self.ip = config["ip"]
        self.port = config["port"]
        self.baudrate = config["baudrate"]
        self.address = config["address"]


    def set_fingers(self, fingers):
        """
        fingers: dict {aux, flex, index, middle, ring, little} [0-100]
        """

        param = rm_peripheral_read_write_params_t(1, 1070, self.address, 6)
        ret = self.arm_controller.rm_write_registers(param, [fingers["flex"], fingers["aux"], fingers["middle"],fingers["index"],fingers["little"],fingers["ring"]])
        return ret
    def _main(self):
        
        time.sleep(0.1)

    def _connect_device(self) -> bool:
        """连接设备"""
        try:
            self.handle = self.arm_controller.rm_create_robot_arm(self.ip, self.port) 
            if self.handle.id == -1:
                raise ConnectionError(f"Failed to connect to robot arm at {self.ip}:{self.port}")

            code = self.arm_controller.rm_set_modbus_mode(1, 460800, 2)
            print(f"[Initialize]Set modbus mode,code: {code}")
            if code != 0 :
                raise RuntimeError(f"Failed to set modbus mode,error code: {code}")
            
            param = rm_peripheral_read_write_params_t(1, 901, self.address)
            code,result = self.arm_controller.rm_read_holding_registers(param)

            print(f"[Initialize]Get hand type,code: {code},result: {result}")

            if code:
                raise RuntimeError(f"Failed to get hand type,error code: {code}")
            elif result+self.address != 128:
                raise RuntimeError(f"Hand type mismatch,expected {128-self.address},got {result}")
                    
            return True
            
        except Exception as e:
            self.arm_controller.rm_delete_robot_arm()
            return False
        
    def _disconnect_device(self) -> bool:
        """
        断开与机械臂的连接
        :return: 是否成功断开连接
        """
        try:
            
            # 断开机械臂连接
            if self.arm_controller is not None and self.handle is not None:
                # 调用SDK接口断开连接
                self.arm_controller.rm_delete_robot_arm()
                self.handle = None
            
            print(f"[Disconnect] Robot arm disconnected from {self.ip}:{self.port}")
            return True
            
        except Exception as e:
            print(f"Error disconnecting robot arm: {str(e)}")
            return False
        
    def start_control(self):
        if not self.is_controlling:
            self.is_controlling = True
            self.control_thread_running = True
            
            # 启动控制线程
            self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
            self.control_thread.start()
            
            print("[Control] Control started.")
    
    def stop_control(self):
         if self.is_controlling:
            self.is_controlling = False
            self.control_thread_running = False
            
            # 等待控制线程结束
            if self.control_thread and self.control_thread.is_alive():
                self.control_thread.join(timeout=1.0)

            # 清空队列
            self.hand_queue.clear()
            
            print("[Control] Control stopped.")

    def _control_loop(self):
        while self.control_thread_running:
            latest_data = None
            # 获取最新的数据，但不移除队列中的元素
            if len(self.hand_queue) > 0:
                latest_data = self.hand_queue[-1]  # 获取最新的数据（deque的最后一个元素）
            
            # 如果有新数据，则执行控制
            if latest_data is not None:
                self.fingers = self.set_fingers(latest_data)
            
            # 添加一个小延时以控制循环频率
            time.sleep(0.01)
