import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Components.TeleopMiddleware import TeleopMiddleware
from Components.DataCollect import DataCollect
from Device.VR.VRSocket import VRSocket
from Device.Robot.TestRobot import TestRobot
from Device.Camera.TestCamera import TestCamera
import time

if __name__ == '__main__':
    try:
        dc = DataCollect()
        l_arm = TestRobot({"fps": 30})
        r_arm = TestRobot({"fps": 30})
        vrsocket = VRSocket({"ip": '192.168.0.20', "port": 12345})
        teleop = TeleopMiddleware()
        # camera1 = RealSenseCamera({"serial":"153122070447","target_fps": 30}) 
        camera1 = TestCamera({"fps": 30})
        
        devices = [l_arm, r_arm, vrsocket, camera1]
        @camera1.on("frame")
        def show_frame(frame):
            dc.put_video_frame(frame)
        
        l_arm.on("state", dc.put_robot_state)
        
        # 注册回调函数
        teleop.on("leftGripDown",l_arm.start_control)
        teleop.on("leftGripUp",l_arm.stop_control)
        teleop.on("rightGripDown",r_arm.start_control)
        teleop.on("rightGripUp",r_arm.stop_control)
        
        teleop.on("buttonATurnDown",dc.toggle_capture_state)
        
        #注册回调函数
        # vrsocket.on("message",teleop.handle_socket_data)
        @vrsocket.on("message")
        def teleop_handle_socket_data(message):
            print(message)
            teleop.handle_socket_data(message)

        @dc.on("status_change")
        def print_status(state):
            print(f"数据采集状态: {state}")
        
        dc.start()
        camera1.start()
        l_arm.start()
        r_arm.start()
        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)