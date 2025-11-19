"""
本程序测试使用手柄扳机控制末端灵巧手和机械臂的效果
利用VR手柄的扳机控制4指的弯曲度，控制灵巧手
"""
from EasyTeleop.Components import TeleopMiddleware, HandVisualizer
from EasyTeleop.Device.VR import VRSocket
from EasyTeleop.Device.Hand import Revo2Direct
import numpy as np
import time

if __name__ == '__main__':
    try:
        is_control = False

        r_hand = Revo2Direct({"port": "com3", "slave_id": 0x7e,"control_fps":80, "hand_side": "left"}) 
        l_hand = Revo2Direct({"port": "com4", "slave_id": 0x7f,"control_fps":80, "hand_side": "right"}) 
        vrsocket = VRSocket({"ip": '192.168.0.103', "port": 12345})
        teleop = TeleopMiddleware()
        
        devices = [r_hand ,l_hand, vrsocket]
        
        #注册回调函数
        @vrsocket.on("message")
        def teleop_handle_socket_data(message):
            if message['type'] == "hand":
                left_hand_values = [0, 0, 0, 0, 0, 0]
                right_hand_values = [0, 0, 0, 0, 0, 0]
                # 计算并打印左手灵巧手控制值
                if 'leftHand' in message['payload'] and message['payload']['leftHand']['isTracked']:

                    left_hand_values = l_hand.handle_openxr(message['payload']['leftHand'])

                    if left_hand_values != [0, 0, 0, 0, 0, 0]:
                        print(left_hand_values)
                        l_hand.add_hand_data(left_hand_values)

                # 计算并打印右手灵巧手控制值
                if 'rightHand' in message['payload'] and message['payload']['rightHand']['isTracked']:

                    right_hand_values = r_hand.handle_openxr(message['payload']['rightHand'])
                    # print(f"右手灵巧手控制值: {right_hand_values}")
                    if right_hand_values != [0, 0, 0, 0, 0, 0]:

                        r_hand.add_hand_data(right_hand_values)

            teleop.handle_socket_data(message)
        
        
        r_hand.start()
        l_hand.start()
        vrsocket.start() 

        l_hand.start_control()
        r_hand.start_control()

        # visualizer.start()
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)