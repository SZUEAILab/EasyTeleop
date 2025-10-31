"""
本程序测试使用手柄扳机控制末端灵巧手和机械臂的效果
利用VR手柄的扳机控制4指的弯曲度，控制灵巧手
"""
from EasyTeleop.Components import TeleopMiddleware
from EasyTeleop.Device.VR import VRSocket
from EasyTeleop.Device.Robot import RealMan
from EasyTeleop.Device.Hand import Revo2OnRealMan
import time

if __name__ == '__main__':
    try:
        arm = RealMan({"ip": "192.168.0.19", "port": 8080})
        hand = Revo2OnRealMan({"ip": "192.168.0.19", "port": 8080,"baudrate":460800, "address": 127}) 
        vrsocket = VRSocket({"ip": '192.168.0.103', "port": 12345})
        teleop = TeleopMiddleware()
        
        
        devices = [arm, hand, vrsocket]
        
        # 注册回调函数
        teleop.on("rightPosRot",arm.add_pose_data)
        @teleop.on("rightGripTurnDown")
        def control_l_arm():
            print("开始控制机械臂")
            arm.start_control()
            hand.start_control()
        @teleop.on("rightGripTurnUp")
        def control_l_arm_stop():
            print("停止控制机械臂")
            arm.stop_control()
            hand.stop_control()
        @teleop.on("rightTrigger")
        def control_l_arm_hand(trigger):
            # print(f"触发器原始值: {trigger}")
            trigger = int((1-trigger)*100) #限制在0-1之间
            fingers = [trigger, trigger, trigger, trigger, trigger, trigger]
            hand.add_hand_data(fingers)
        

        @teleop.on("rightStick")
        def stick_callback(state):
            pass
            # print(f"左摇杆: {state}")

        
        #注册回调函数
        vrsocket.on("message",teleop.handle_socket_data)
        
        
        arm.start()
        hand.start()
        vrsocket.start() 
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)