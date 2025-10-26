import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Components import TeleopMiddleware
from Device.VR.VRSocket import VRSocket
from Device.Robot.RealMan import RealMan
import time

if __name__ == '__main__':
    try:
        arm = RealMan({"ip": "192.168.0.17", "port": 8080})
        vrsocket = VRSocket({"ip": '192.168.0.100', "port": 12345})
        teleop = TeleopMiddleware()
        
        devices = [arm, vrsocket]
        
        # 注册回调函数

        teleop.on("rightGripTurnDown",arm.start_control)
        teleop.on("rightGripTurnUp",arm.stop_control)
        teleop.on("rightPosRot",arm.add_pose_data)
        teleop.on("rightTrigger",arm.add_end_effector_data)
        
        #注册回调函数
        vrsocket.on("message",teleop.handle_socket_data)

        arm.start()
        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)