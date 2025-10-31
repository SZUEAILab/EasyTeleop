"""
本程序测试使用手柄扳机控制末端灵巧手和机械臂的效果
利用VR手柄的扳机控制4指的弯曲度，控制灵巧手
"""
from EasyTeleop.Components import TeleopMiddleware, HandVisualizer
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
        visualizer = HandVisualizer()
        
        
        devices = [arm, hand, vrsocket]
        
        teleop.on("rightPosRot",arm.add_pose_data)
        #注册回调函数
        @vrsocket.on("message")
        def teleop_handle_socket_data(message):
            if message['type'] == "hand":
                visualizer.add_data(message['payload'])
                left_hand_values = [0, 0, 0, 0, 0, 0]
                right_hand_values = [0, 0, 0, 0, 0, 0]
                # 计算并打印左手灵巧手控制值
                if 'leftHand' in message['payload'] and message['payload']['leftHand']['isTracked']:
                    pass
                # 计算并打印右手灵巧手控制值
                if 'rightHand' in message['payload'] and message['payload']['rightHand']['isTracked']:
                    right_hand_values = hand.handle_openxr(message['payload']['rightHand'])
                    if right_hand_values != [0, 0, 0, 0, 0, 0]:
                        hand.add_hand_data(right_hand_values)
                # if right_hand_values[0] > 20 and right_hand_values[1] > 40 and right_hand_values[2] > 40 and right_hand_values[3] >40 and right_hand_values[4] >40:
                #     arm.start_control()
                # if left_hand_values[0] > 20 and left_hand_values[1] > 40 and left_hand_values[2] > 40 and left_hand_values[3] >40 and left_hand_values[4] >40:
                #     arm.stop_control()

            teleop.handle_socket_data(message)
        
        
        arm.start()
        hand.start()
        vrsocket.start() 

        hand.start_control()

        # visualizer.start()
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)