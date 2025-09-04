from Teleoperation import Teleoperation
from VRSocket import VRSocket
from Robots.RealMan import RM_controller

if __name__ == '__main__':
    # 配置
    VR_IP = '192.168.0.20'
    VR_PORT = 12345
    L_RM_IP = '192.168.0.18'
    R_RM_IP = '192.168.0.19'
    try:
        l_arm = RM_controller(L_RM_IP)
        r_arm = RM_controller(R_RM_IP)
        l_arm.start()
        r_arm.start()
        # 启动遥操作
        vrsocket = VRSocket(VR_IP, VR_PORT)
        
        teleop = Teleoperation()
        # 注册回调函数
        teleop.on("leftGripDown",l_arm.start_control)
        teleop.on("leftGripUp",l_arm.stop_control)
        teleop.on("rightGripDown",r_arm.start_control)
        teleop.on("rightGripUp",r_arm.stop_control)
        
        #注册回调函数
        vrsocket.on_message(teleop.handle_socket_data)
        # 下面这种写法也行
        # @vrsocket.on_message
        # def handle_message(msg):
        #     teleop.handle_socket_data(msg)
        
        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响
        
        teleop.start() #暂时啥都没有,就是个while阻止主线程退出的
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)