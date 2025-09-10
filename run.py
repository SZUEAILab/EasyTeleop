from Teleoperation import Teleoperation
from VRSocket import VRSocket
from Robots.RealMan import RM_controller
from DataCollect import DataCollect

if __name__ == '__main__':
    try:
        dc = DataCollect()
        dc.start()
        
        l_arm = RM_controller({"ip": "192.168.0.18", "port": 8080})
        r_arm = RM_controller({"ip": "192.168.0.19", "port": 8080})

        def print_left_arm_state(state):
            dc.put_robot_state(state)
            # print(f"Left Arm State: {state}")

        # l_arm.on("state", print_left_arm_state)

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