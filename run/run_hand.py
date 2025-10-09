"""
本程序测试使用手柄扳机控制末端灵巧手和机械臂的效果
利用VR手柄的扳机控制4指的弯曲度，控制灵巧手
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Components import TeleopMiddleware, DataCollect
from Device.VR.VRSocket import VRSocket
from Device.Robot.RealMan import RealMan
from Device.Hand.Revo2OnRealMan import Revo2OnRealMan
import time
import math

if __name__ == '__main__':
    try:
        l_arm = RealMan({"ip": "192.168.0.17", "port": 8080})
        l_hand = Revo2OnRealMan({"ip": "192.168.0.17", "port": 8080,"baudrate":460800, "address": 126}) 
        vrsocket = VRSocket({"ip": '192.168.0.20', "port": 12345})
        teleop = TeleopMiddleware()
        
        
        devices = [l_arm, l_hand, vrsocket]
        
        # 注册回调函数
        @teleop.on("leftGripDown")
        def control_l_arm_hand(state,trigger):
            l_arm.start_control(state)
        teleop.on("leftGripUp",l_arm.stop_control)

        @teleop.on("leftStick")
        def stick_callback(state):
            l_hand.fingers["flex"] = 70+int(state['x']*50)
            # print(f"左摇杆: {state}")

        
        #注册回调函数
        @vrsocket.on("message")
        def teleop_callback(message):
            teleop.handle_socket_data(message)
            print(f"VR手柄数据: {message}")
        
        
        l_arm.start()
        l_hand.start()
        vrsocket.start() 
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)
        