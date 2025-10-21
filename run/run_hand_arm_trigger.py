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
        l_hand = Revo2OnRealMan({"ip": "192.168.0.17", "port": 8080,"baudrate":460800, "address": 127}) 
        vrsocket = VRSocket({"ip": '192.168.0.103', "port": 12345})
        teleop = TeleopMiddleware()
        
        
        devices = [l_arm, l_hand, vrsocket]
        
        # 注册回调函数
        teleop.on("rightPosRot",l_arm.add_pose_data)
        @teleop.on("rightGripTurnDown")
        def control_l_arm():
            print("开始控制机械臂")
            l_arm.start_control()
        teleop.on("rightGripTurnUp",l_arm.stop_control)
        @teleop.on("rightTrigger")
        def control_l_arm_hand(trigger):
            l_arm.add_gripper_data(trigger)
            # print(f"触发器原始值: {trigger}")
            trigger = int((1-trigger)*100) #限制在0-1之间
            # print(f"触发器: {trigger}")
            
            # l_hand.set_fingers(fingers)
            l_hand.fingers["aux"] = int(trigger)
            l_hand.fingers["index"] = trigger
            l_hand.fingers["middle"] = int(trigger)
            l_hand.fingers["ring"] = int(trigger*0.9)
            l_hand.fingers["little"] = int(trigger*0.8)
        

        @teleop.on("rightStick")
        def stick_callback(state):
            l_hand.fingers["flex"] = 70+int(state['x']*50)
            # print(f"左摇杆: {state}")

        
        #注册回调函数
        vrsocket.on("message",teleop.handle_socket_data)
        
        
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