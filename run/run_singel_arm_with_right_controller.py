from EasyTeleop.Components import TeleopMiddleware
from EasyTeleop.Device.VR import VRSocket
from EasyTeleop.Device.Robot import RealManWithIK
import time

if __name__ == '__main__':
    try:
        start_time = 0
        package_count = 0
        
        arm = RealManWithIK({"ip": "192.168.0.19", "port": 8080,"control_mode": 1})
        vrsocket = VRSocket({"ip": '192.168.0.103', "port": 12345})
        teleop = TeleopMiddleware()
        
        devices = [arm, vrsocket]
        

        teleop.on("rightGripTurnDown",arm.start_control)
        teleop.on("rightGripTurnUp",arm.stop_control)
        teleop.on("rightPosRot",arm.add_pose_data)
        teleop.on("rightTrigger",arm.add_end_effector_data)
        
        #注册回调函数
        @vrsocket.on("message")
        def handle_socket_data(data):
            # global start_time, package_count
            # if(start_time == 0):
            #     start_time = time.time()
            #     ackage_count += 1
            # else:
            #     package_count += 1
            #     print(f"fps{package_count / (time.time() - start_time):.2f}")
            teleop.handle_socket_data(data)

        arm.start()
        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)
