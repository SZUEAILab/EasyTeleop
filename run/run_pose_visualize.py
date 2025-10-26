import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Components import TeleopMiddleware,Visualizer
from Device.VR.VRSocket import VRSocket
import time

if __name__ == '__main__':
    try:
        visualizer = Visualizer()
        vrsocket = VRSocket({"ip": '192.168.0.100', "port": 12345})
        teleop = TeleopMiddleware()
        
        devices = [vrsocket]

        @vrsocket.on("message")
        def teleop_handle_socket_data(message):
            # print(message)
            if message['type'] == "controller":
                # 修改为分别向左手和右手队列添加数据
                payload = message['payload']
                # 左手数据
                left_rotation = payload.get('leftQuat', payload['leftRot'])
                visualizer.add_left_data({
                    "position": payload['leftPos'],
                    "rotation": left_rotation
                })
                
                # 右手数据
                right_rotation = payload.get('rightQuat', payload['rightRot'])
                visualizer.add_right_data({
                    "position": payload['rightPos'],
                    "rotation": right_rotation
                })
            elif message['type'] == "hand":
                # 添加左手数据
                if message['payload']['leftHand']['isTracked']:
                    visualizer.add_left_data(message['payload']['leftHand']['rootPose'])
                # 添加右手数据
                if message['payload']['rightHand']['isTracked']:
                    print(message['payload']['rightHand']['rootPose'])
                    visualizer.add_right_data(message['payload']['rightHand']['rootPose'])
            # teleop.handle_socket_data(message)

        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响

        visualizer.start()
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)