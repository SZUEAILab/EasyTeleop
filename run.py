from Teleoperation import Teleoperation
from VRSocket import VRSocket
from Robots.RealMan import RM_controller
from DataCollect import DataCollect
from Camera.RealSenseCamera import RealSenseCamera
import cv2

if __name__ == '__main__':
    try:
        camera1 = RealSenseCamera({"serial":"427622270277"})
        camera1.connect()
        for i in range(50):
            
            color_frame, depth_frame = camera1.get_frames()
            depth_frame = cv2.applyColorMap(cv2.convertScaleAbs(depth_frame, alpha=0.03), cv2.COLORMAP_JET)
            
            if color_frame is not None and depth_frame is not None:
                try:
                    cv2.imshow("Color", color_frame)
                    cv2.imshow("Depth", depth_frame)
                    cv2.waitKey(500)
                except cv2.error as e:
                    print(f"Display error (but frames are OK): {e}")


        dc = DataCollect()
        dc.start()
        
        l_arm = RM_controller({"ip": "192.168.0.18", "port": 8080})
        r_arm = RM_controller({"ip": "192.168.0.19", "port": 8080})

        def print_left_arm_state(state):
            dc.put_robot_state(state)
            # print(f"Left Arm State: {state}")

        l_arm.on("state", print_left_arm_state)

        l_arm.start()
        r_arm.start()
        # 启动遥操作
        vrsocket = VRSocket({"ip": '192.168.0.20', "port": 12345})
        
        teleop = Teleoperation()
        # 注册回调函数
        teleop.on("leftGripDown",l_arm.start_control)
        teleop.on("leftGripUp",l_arm.stop_control)
        teleop.on("rightGripDown",r_arm.start_control)
        teleop.on("rightGripUp",r_arm.stop_control)
        
        #注册回调函数
        vrsocket.on("message",teleop.handle_socket_data)
        
        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响
        
        while(1):
            pass
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)