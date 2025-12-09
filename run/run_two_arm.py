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
        camera2 = RealSenseCamera({"serial":"427622270438","target_fps": 30}) 
        camera3 = RealSenseCamera({"serial":"427622270277","target_fps": 30}) 
        
        devices = [l_arm, r_arm, vrsocket, camera1,camera2,camera3]
        
        @camera1.on("frame")
        def show_frame(frame):
            dc.put_video_frame(frame,camera_id=0)

        @camera2.on("frame")
        def show_frame(frame):
            dc.put_video_frame(frame,camera_id=1)

        @camera3.on("frame")
        def show_frame(frame):
            dc.put_video_frame(frame,camera_id=2)
            
        
        # 创建一个函数来处理左臂位姿数据
        @l_arm.on("pose")
        def handle_left_arm_pose(pose_data):
            if pose_data is not None:
                # 将pose数据传递，指定臂ID为0
                dc.put_robot_pose(pose_data, arm_id=0)
        
        # 创建一个函数来处理左臂关节数据
        @l_arm.on("joint")
        def handle_left_arm_joint(joint_data):
            if joint_data is not None:
                # 将joint数据传递，指定臂ID为0
                dc.put_robot_joint(joint_data, arm_id=0)
        
        # 创建一个函数来处理右臂位姿数据
        @r_arm.on("pose")
        def handle_right_arm_pose(pose_data):
            if pose_data is not None:
                # 将pose数据传递，指定臂ID为1
                dc.put_robot_pose(pose_data, arm_id=1)
        
        # 创建一个函数来处理右臂关节数据
        @r_arm.on("joint")
        def handle_right_arm_joint(joint_data):
            if joint_data is not None:
                # 将joint数据传递，指定臂ID为1
                dc.put_robot_joint(joint_data, arm_id=1)
        
        # 处理左臂夹爪数据
        @l_arm.on("end_effector")
        def handle_left_end_effector_state(end_effector):
            if end_effector is not None:
                dc.put_end_effector_state(end_effector, arm_id=0)
        
        # 处理右臂夹爪数据
        @r_arm.on("end_effector")
        def handle_right_end_effector_state(end_effector):
            if end_effector is not None:
                dc.put_end_effector_state(end_effector, arm_id=1)
        
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

        @dc.on("status_change")
        def status_change(status):
            print(f"数据采集状态改变: {status}")    
        
        #注册回调函数
        vrsocket.on("message",teleop.handle_socket_data)
        
        dc.start()
        camera1.start()
        camera2.start()
        camera3.start()
        l_arm.start()
        r_arm.start()
        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")