import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Components import TeleopMiddleware,HandVisualizer
from Components.DataCollect import DataCollect
from Device.VR.VRSocket import VRSocket
from Device.Robot.TestRobot import TestRobot
from Device.Camera.TestCamera import TestCamera
from Device.Robot.RealMan import RealMan
import time

if __name__ == '__main__':
    try:
        visualizer = HandVisualizer()
        vrsocket = VRSocket({"ip": '192.168.0.100', "port": 12345})
        teleop = TeleopMiddleware()
        
        devices = [vrsocket]
        @vrsocket.on("message")
        def teleop_handle_socket_data(message):
            if message['type'] == "hand":
                print(message)
                visualizer.add_data(message['payload'])
            teleop.handle_socket_data(message)

        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响

        visualizer.start()
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)