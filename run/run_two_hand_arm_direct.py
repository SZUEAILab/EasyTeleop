"""

"""
from EasyTeleop.Components import TeleopMiddleware, HandVisualizer
from EasyTeleop.Device.VR import VRSocket
from EasyTeleop.Device.Robot import RealManWithIK
from EasyTeleop.Device.Hand import Revo2Direct
import time
import numpy as np
    
def euler_from_quaternion(quat):
    """
    手动实现四元数转欧拉角（XYZ旋转顺序，右手坐标系）
    :param quat: 四元数列表，格式为 [x, y, z, w]（实部为w，虚部为x/y/z）
    :return: 欧拉角 (roll, pitch, yaw)，单位为弧度（对应X/Y/Z轴旋转）
    """
    import math

    x, y, z, w = quat  # 解包四元数分量
    
    # 1. 计算滚转角（roll，X轴旋转）
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)  # 范围：[-π, π]
    
    # 2. 计算俯仰角（pitch，Y轴旋转）
    sinp = 2 * (w * y - z * x)
    # 防止数值溢出（因浮点计算误差，sinp可能超出[-1,1]）
    sinp = min(max(sinp, -1.0), 1.0)
    pitch = math.asin(sinp)  # 范围：[-π/2, π/2]
    
    # 3. 计算偏航角（yaw，Z轴旋转）
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)  # 范围：[-π, π]
    
    return roll, pitch, yaw

if __name__ == '__main__':
    try:
        is_control = False

        r_arm = RealManWithIK({"ip": "192.168.0.19", "port": 8080})
        r_hand = Revo2Direct({"port": "/dev/ttyUSB0", "slave_id": 0x7e,"control_fps":80, "hand_side": "left"}) 
        
        l_arm = RealManWithIK({"ip": "192.168.0.18", "port": 8080})
        l_hand = Revo2Direct({"port": "/dev/ttyUSB1", "slave_id": 0x7f,"control_fps":80, "hand_side": "right"}) 
        vrsocket = VRSocket({"ip": '192.168.0.103', "port": 12345})
        teleop = TeleopMiddleware()
        visualizer = HandVisualizer()
        
        
        devices = [r_arm, r_hand ,l_arm,l_hand, vrsocket]
        
        teleop.on("rightPosRot",r_arm.add_pose_data)
        #注册回调函数
        @vrsocket.on("message")
        def teleop_handle_socket_data(message):
            global is_control
            if message['type'] == "hand":
                visualizer.add_data(message['payload'])
                left_hand_values = [0, 0, 0, 0, 0, 0]
                right_hand_values = [0, 0, 0, 0, 0, 0]
                # 计算并打印左手灵巧手控制值
                if 'leftHand' in message['payload'] and message['payload']['leftHand']['isTracked']:
                    _position = message['payload']['leftHand']['rootPose']['position']
                    _quantity = message['payload']['leftHand']['rootPose']['rotation']
                    # 确保四元数数据是数值类型而不是字符串
                    _quantity = [float(_quantity['x']), float(_quantity['y']), float(_quantity['z']), float(_quantity['w'])]
                    _rotation = euler_from_quaternion(_quantity)
                    _pose_quant = [_position['x'],_position['y'],_position['z'], *_rotation]
                    # print(_pose_quant)
                    l_arm.add_pose_data(_pose_quant)

                    left_hand_values = l_hand.handle_openxr(message['payload']['leftHand'])

                    if left_hand_values != [0, 0, 0, 0, 0, 0]:
                        l_hand.add_hand_data(left_hand_values)

                # 计算并打印右手灵巧手控制值
                if 'rightHand' in message['payload'] and message['payload']['rightHand']['isTracked']:
                    _position = message['payload']['rightHand']['rootPose']['position']
                    _quantity = message['payload']['rightHand']['rootPose']['rotation']
                    # 确保四元数数据是数值类型而不是字符串
                    _quantity = [float(_quantity['x']), float(_quantity['y']), float(_quantity['z']), float(_quantity['w'])]
                    _rotation = euler_from_quaternion(_quantity)
                    _pose_quant = [_position['x'],_position['y'],_position['z'], *_rotation]
                    # print(_pose_quant)
                    r_arm.add_pose_data(_pose_quant)

                    right_hand_values = r_hand.handle_openxr(message['payload']['rightHand'])
                    # print(f"右手灵巧手控制值: {right_hand_values}")
                    if right_hand_values != [0, 0, 0, 0, 0, 0]:

                        r_hand.add_hand_data(right_hand_values)
                # if right_hand_values[0] > 20 and right_hand_values[1] > 40 and right_hand_values[2] > 40 and right_hand_values[3] >40 and right_hand_values[4] >40:
                #     l_arm.start_control()
                #     r_arm.start_control()
                # if left_hand_values[0] > 20 and left_hand_values[1] > 40 and left_hand_values[2] > 40 and left_hand_values[3] >40 and left_hand_values[4] >40:
                #     l_arm.start_control()
                #     r_arm.start_control()
                if left_hand_values[2] > 60 and left_hand_values[3] > 60 and left_hand_values[4] >60 and left_hand_values[5] >60 and right_hand_values[2] > 60 and right_hand_values[3] > 60 and right_hand_values[4] >60 and right_hand_values[5] >60:
                    if is_control:
                        is_control = False
                        print("停止控制机械臂")
                        l_arm.stop_control()
                        r_arm.stop_control()
                else:
                    if not is_control:
                        is_control = True
                        print("开始控制机械臂")
                        l_arm.start_control() 
                        r_arm.start_control()

            teleop.handle_socket_data(message)
        
        
        r_arm.start()
        r_hand.start()
        l_arm.start()
        l_hand.start()
        vrsocket.start() 

        l_hand.start_control()
        r_hand.start_control()

        # visualizer.start()
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)