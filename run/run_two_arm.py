from EasyTeleop.Components import TeleopMiddleware, DataCollect
from EasyTeleop.Device.VR import VRSocket
from EasyTeleop.Device.Robot import RealMan,RealManWithIK
from EasyTeleop.Device.Camera import RealSenseCamera
import time

if __name__ == '__main__':
    try:
        RealSenseCamera.find_device()
        dc = DataCollect()
        l_arm = RealManWithIK({"ip": "192.168.0.18", "port": 8080})
        r_arm = RealManWithIK({"ip": "192.168.0.19", "port": 8080})
        vrsocket = VRSocket({"ip": '192.168.0.103', "port": 12345})
        teleop = TeleopMiddleware()
        camera1 = RealSenseCamera({"serial":"153122070447","target_fps": 30}) 
        
        devices = [l_arm, r_arm, vrsocket, camera1]
        
        @camera1.on("frame")
        def show_frame(frame):
            dc.put_video_frame(frame)
        
        # 创建一个函数来处理机器人状态数据，将其格式化为(pose, joints)元组
        def handle_robot_state(timestamp=None):
            def inner_func(*args):
                # args可能包含多个参数，但我们只关心pose和joint数据
                pose_data = l_arm.get_pose_data()
                joint_data = l_arm.get_joint_data()
                if pose_data is not None and joint_data is not None:
                    # 将pose和joint数据作为元组传递
                    dc.put_robot_state((pose_data, joint_data), timestamp)
            return inner_func
        
        # 注册机器人状态事件处理函数
        l_arm.on("pose", handle_robot_state())
        l_arm.on("joint", handle_robot_state())
        
        # 注册回调函数
        teleop.on("leftGripTurnDown",l_arm.start_control)
        teleop.on("leftGripTurnUp",l_arm.stop_control)
        teleop.on("leftPosRot",l_arm.add_pose_data)
        teleop.on("leftTrigger",l_arm.add_end_effector_data)

        teleop.on("rightGripTurnDown",r_arm.start_control)
        teleop.on("rightGripTurnUp",r_arm.stop_control)
        teleop.on("rightPosRot",r_arm.add_pose_data)
        teleop.on("rightTrigger",r_arm.add_end_effector_data)
        
        teleop.on("buttonATurnDown",dc.toggle_capture_state)
        
        #注册回调函数
        vrsocket.on("message",teleop.handle_socket_data)
        
        dc.start()
        # camera1.start()
        l_arm.start()
        r_arm.start()
        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")