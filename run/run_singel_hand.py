"""
本程序测试使用手柄扳机控制末端灵巧手和机械臂的效果
利用VR手柄的扳机控制4指的弯曲度，控制灵巧手
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Components import TeleopMiddleware, HandVisualizer
from Device.VR.VRSocket import VRSocket
from Device.Robot.RealMan import RealMan
from Device.Hand.Revo2OnRealMan import Revo2OnRealMan
import time
import numpy as np

def calculate_hand_values(hand_data):
    """
    根据OpenXR手部骨架数据计算灵巧手控制值
    返回6个0-100的值，前五个表示手指弯曲程度，第六个表示大拇指向掌心收拢的程度
    
    Args:
        hand_data: OpenXR手部数据，包含joints数组和rootPose
        
    Returns:
        list: 6个0-100的值，分别对应拇指、食指、中指、无名指、小指的弯曲程度和拇指收拢程度
    """
    if not hand_data or not hand_data.get('isTracked') or not hand_data.get('joints'):
        return [0, 0, 0, 0, 0, 0]
    
    joints = hand_data['joints']
    if len(joints) != 26:  # OpenXR定义的26个关节
        return [0, 0, 0, 0, 0, 0]
    
    # OpenXR关节索引常量
    XR_HAND_JOINT_PALM_EXT = 0
    XR_HAND_JOINT_WRIST_EXT = 1
    XR_HAND_JOINT_THUMB_METACARPAL_EXT = 2
    XR_HAND_JOINT_THUMB_PROXIMAL_EXT = 3
    XR_HAND_JOINT_THUMB_DISTAL_EXT = 4
    XR_HAND_JOINT_THUMB_TIP_EXT = 5
    XR_HAND_JOINT_INDEX_METACARPAL_EXT = 6
    XR_HAND_JOINT_INDEX_PROXIMAL_EXT = 7
    XR_HAND_JOINT_INDEX_INTERMEDIATE_EXT = 8
    XR_HAND_JOINT_INDEX_DISTAL_EXT = 9
    XR_HAND_JOINT_INDEX_TIP_EXT = 10
    XR_HAND_JOINT_MIDDLE_METACARPAL_EXT = 11
    XR_HAND_JOINT_MIDDLE_PROXIMAL_EXT = 12
    XR_HAND_JOINT_MIDDLE_INTERMEDIATE_EXT = 13
    XR_HAND_JOINT_MIDDLE_DISTAL_EXT = 14
    XR_HAND_JOINT_MIDDLE_TIP_EXT = 15
    XR_HAND_JOINT_RING_METACARPAL_EXT = 16
    XR_HAND_JOINT_RING_PROXIMAL_EXT = 17
    XR_HAND_JOINT_RING_INTERMEDIATE_EXT = 18
    XR_HAND_JOINT_RING_DISTAL_EXT = 19
    XR_HAND_JOINT_RING_TIP_EXT = 20
    XR_HAND_JOINT_LITTLE_METACARPAL_EXT = 21
    XR_HAND_JOINT_LITTLE_PROXIMAL_EXT = 22
    XR_HAND_JOINT_LITTLE_INTERMEDIATE_EXT = 23
    XR_HAND_JOINT_LITTLE_DISTAL_EXT = 24
    XR_HAND_JOINT_LITTLE_TIP_EXT = 25
    
    def get_joint_position(joint):
        """获取关节位置"""
        return np.array([joint['position']['x'], joint['position']['y'], joint['position']['z']])
    def calculate_bone_bend(joint1, joint2, joint3):
        vec1 = get_joint_position(joint2) - get_joint_position(joint1)
        vec2 = get_joint_position(joint3) - get_joint_position(joint2)
        cos_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        # 限制在[-1, 1]范围内，防止数值误差
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle)
        return angle/ (2 * np.pi) *360
    def calculate_finger_bend(joint1, joint2, joint3, joint4):
        """
        计算手指弯曲程度
        通过计算三个关节角度来确定弯曲程度
        """
        # 计算关节向量
        vec1 = get_joint_position(joint2) - get_joint_position(joint1)
        vec2 = get_joint_position(joint3) - get_joint_position(joint2)
        vec3 = get_joint_position(joint4) - get_joint_position(joint3)
        
        # 计算关节间角度
        # 使用向量夹角公式: cos(theta) = (a·b)/(|a||b|)
        def angle_between_vectors(v1, v2):
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            # 限制在[-1, 1]范围内，防止数值误差
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle = np.arccos(cos_angle)
            return angle
        
        angle1 = angle_between_vectors(vec1, vec2)
        angle2 = angle_between_vectors(vec2, vec3)
        
        # 将角度转换为0-100的弯曲程度值
        # 弯曲角度越大，值越接近100
        bend_value = (angle1 + angle2) / (2 * np.pi) * 100
        return np.clip(bend_value, 0, 100)
    
    def calculate_thumb_towards_palm(wrist, palm, thumb_m, thumb_p, thumb_d):
        """
        计算拇指收拢程度（向掌心方向）
        通过计算thumb_index_normal和palm_normal两个法向量的夹角来确定
        """
        try:
            # 获取关节位置
            wrist_pos = get_joint_position(wrist)
            palm_pos = get_joint_position(palm)
            thumb_m_pos = get_joint_position(thumb_m)
            thumb_p_pos = get_joint_position(thumb_p)
            
            # 计算手掌平面的法向量（使用手腕、手掌和食指根部）
            index_proximal_pos = get_joint_position(joints[XR_HAND_JOINT_INDEX_PROXIMAL_EXT])
            palm_vec1 = palm_pos - wrist_pos
            palm_vec2 = index_proximal_pos - wrist_pos
            palm_normal = np.cross(palm_vec1, palm_vec2)
            
            # 检查零向量
            if np.linalg.norm(palm_normal) == 0:
                return 50.0  # 返回默认值
            
            # 计算拇指第一根骨头和食指第一根骨头的平面法向量（从metacarpal到proximal）
            thumb_bone_vec = thumb_p_pos - thumb_m_pos
            index_bone_vec = index_proximal_pos - thumb_m_pos

            thumb_index_normal = np.cross(index_bone_vec,thumb_bone_vec)
            
            # 计算thumb_index_normal和palm_normal两个法向量的夹角
            cos_angle = np.dot(palm_normal, thumb_index_normal) / (
                np.linalg.norm(palm_normal) * np.linalg.norm(thumb_index_normal)
            )
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle = np.arccos(np.abs(cos_angle))  # 使用绝对值计算夹角
            # print(f"angel: {angle}")
            
            # 将夹角映射到0-100范围
            # 0度时为100（完全收拢），90度时为0（完全张开）
            thumb_towards_palm = angle / (np.pi/2) * 100
            return np.clip(thumb_towards_palm, 0, 100)
        except Exception as e:
            # 出现异常时返回默认值
            return 50.0
    
    # 计算各手指弯曲程度
    try:
        # 食指弯曲程度 (index finger)
        index_bend = calculate_finger_bend(
            joints[XR_HAND_JOINT_INDEX_METACARPAL_EXT],
            joints[XR_HAND_JOINT_INDEX_PROXIMAL_EXT],
            joints[XR_HAND_JOINT_INDEX_INTERMEDIATE_EXT],
            joints[XR_HAND_JOINT_INDEX_DISTAL_EXT]
        )
        
        # 中指弯曲程度 (middle finger)
        middle_bend = calculate_finger_bend(
            joints[XR_HAND_JOINT_MIDDLE_METACARPAL_EXT],
            joints[XR_HAND_JOINT_MIDDLE_PROXIMAL_EXT],
            joints[XR_HAND_JOINT_MIDDLE_INTERMEDIATE_EXT],
            joints[XR_HAND_JOINT_MIDDLE_DISTAL_EXT]
        )
        
        # 无名指弯曲程度 (ring finger)
        ring_bend = calculate_finger_bend(
            joints[XR_HAND_JOINT_RING_METACARPAL_EXT],
            joints[XR_HAND_JOINT_RING_PROXIMAL_EXT],
            joints[XR_HAND_JOINT_RING_INTERMEDIATE_EXT],
            joints[XR_HAND_JOINT_RING_DISTAL_EXT]
        )
        
        # 小指弯曲程度 (little finger)
        little_bend = calculate_finger_bend(
            joints[XR_HAND_JOINT_LITTLE_METACARPAL_EXT],
            joints[XR_HAND_JOINT_LITTLE_PROXIMAL_EXT],
            joints[XR_HAND_JOINT_LITTLE_INTERMEDIATE_EXT],
            joints[XR_HAND_JOINT_LITTLE_DISTAL_EXT]
        )
        
        # 拇指弯曲程度 (thumb)
        # thumb_bend = calculate_finger_bend(
        #     joints[XR_HAND_JOINT_THUMB_METACARPAL_EXT],
        #     joints[XR_HAND_JOINT_THUMB_PROXIMAL_EXT],
        #     joints[XR_HAND_JOINT_THUMB_DISTAL_EXT],
        #     joints[XR_HAND_JOINT_THUMB_TIP_EXT]
        # )
        thumb_bend = calculate_bone_bend(
            joints[XR_HAND_JOINT_THUMB_METACARPAL_EXT],
            joints[XR_HAND_JOINT_THUMB_PROXIMAL_EXT],
            joints[XR_HAND_JOINT_THUMB_DISTAL_EXT]
        )
        
        # 拇指收拢程度
        thumb_towards_palm = calculate_thumb_towards_palm(
            joints[XR_HAND_JOINT_WRIST_EXT],
            joints[XR_HAND_JOINT_PALM_EXT],
            joints[XR_HAND_JOINT_THUMB_METACARPAL_EXT],
            joints[XR_HAND_JOINT_THUMB_PROXIMAL_EXT],
            joints[XR_HAND_JOINT_THUMB_DISTAL_EXT]
        )
        
        # 返回6个值：拇指弯曲、食指弯曲、中指弯曲、无名指弯曲、小指弯曲、拇指收拢
        return [thumb_bend, index_bend, middle_bend, ring_bend, little_bend, thumb_towards_palm]
        
    except Exception as e:
        # 如果计算过程中出现错误，返回默认值
        print(f"计算手部控制值时出错: {e}")
        return [0, 0, 0, 0, 0, 50]  # 拇指收拢程度默认为50

if __name__ == '__main__':
    try:
        arm = RealMan({"ip": "192.168.0.19", "port": 8080})
        hand = Revo2OnRealMan({"ip": "192.168.0.19", "port": 8080,"baudrate":460800, "address": 127}) 
        vrsocket = VRSocket({"ip": '192.168.0.103', "port": 12345})
        teleop = TeleopMiddleware()
        visualizer = HandVisualizer()
        
        
        devices = [arm, hand, vrsocket]
        
        teleop.on("rightPosRot",arm.add_pose_data)
        #注册回调函数
        @vrsocket.on("message")
        def teleop_handle_socket_data(message):
            if message['type'] == "hand":
                visualizer.add_data(message['payload'])
                left_hand_values = [0, 0, 0, 0, 0, 0]
                right_hand_values = [0, 0, 0, 0, 0, 0]
                # 计算并打印左手灵巧手控制值
                if 'leftHand' in message['payload'] and message['payload']['leftHand']['isTracked']:
                    pass
                # 计算并打印右手灵巧手控制值
                if 'rightHand' in message['payload'] and message['payload']['rightHand']['isTracked']:
                    right_hand_values = hand.handle_openxr(message['payload']['rightHand'])
                    if right_hand_values != [0, 0, 0, 0, 0, 0]:
                        hand.add_hand_data(right_hand_values)
                # if right_hand_values[0] > 20 and right_hand_values[1] > 40 and right_hand_values[2] > 40 and right_hand_values[3] >40 and right_hand_values[4] >40:
                #     arm.start_control()
                # if left_hand_values[0] > 20 and left_hand_values[1] > 40 and left_hand_values[2] > 40 and left_hand_values[3] >40 and left_hand_values[4] >40:
                #     arm.stop_control()

            teleop.handle_socket_data(message)
        
        
        arm.start()
        hand.start()
        vrsocket.start() 

        hand.start_control()

        # visualizer.start()
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)