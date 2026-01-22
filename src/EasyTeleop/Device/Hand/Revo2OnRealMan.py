from .BaseHand import BaseHand
from Robotic_Arm.rm_robot_interface import rm_thread_mode_e,rm_peripheral_read_write_params_t, RoboticArm
import time
import threading
import numpy as np

class Revo2OnRealMan(BaseHand):
    """RealMan通过Modbus驱动Revo2机械手"""

    name = "强脑科技Revo2机械手"
    description = "通过RealMan末端Modbus控制Revo2机械手"
    need_config = {
        "ip": {
            "type": "string",
            "description": "睿尔曼机械臂IP地址",
            "default": "192.168.1.18"
        },
        "port": {
            "type": "integer",
            "description": "睿尔曼机械臂端口号",
            "default": 8080
        },
        "baudrate":{
            "type": "int",
            "description": "Modbus串口波特率",
            "default": 460800
        },
        "address":{
            "type": "int",
            "description": "Revo2机械手Modbus设备地址,左手126，右手127",
            "default": 126
        },
    }
    
    def __init__(self, config):
        self.ip = None
        self.port = None
        self.baudrate = None
        self.address = None
        super().__init__(config)

        self.arm_controller = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)
        self.handle = None
        

    def set_config(self, config):
        """
        设置设备配置，验证配置是否符合need_config要求
        :param config: 配置字典
        :return: 是否设置成功
        """
        # 检查必需的配置字段
        for key in self.need_config:
            if key not in config:
                raise ValueError(f"缺少必需的配置字段: {key}")
        
        self.config = config
        self.ip = config["ip"]
        self.port = config["port"]
        self.baudrate = config["baudrate"]
        self.address = config["address"]


    def set_fingers(self, fingers):
        """
        fingers: ilst [flex, aux, middle, index, little, ring] [0-100]
        """

        param = rm_peripheral_read_write_params_t(1, 1070, self.address, 6)
        ret = self.arm_controller.rm_write_registers(param, fingers)
        return ret
    def _main(self):
        
        time.sleep(0.1)

    def _connect_device(self) -> bool:
        """连接设备"""
        try:
            self.handle = self.arm_controller.rm_create_robot_arm(self.ip, self.port) 
            if self.handle.id == -1:
                raise ConnectionError(f"Failed to connect to robot arm at {self.ip}:{self.port}")

            code = self.arm_controller.rm_set_modbus_mode(1, 460800, 2)
            print(f"[Initialize]Set modbus mode,code: {code}")
            if code != 0 :
                raise RuntimeError(f"Failed to set modbus mode,error code: {code}")
            
            param = rm_peripheral_read_write_params_t(1, 901, self.address)
            code,result = self.arm_controller.rm_read_holding_registers(param)

            print(f"[Initialize]Get hand type,code: {code},result: {result}")

            if code:
                raise RuntimeError(f"Failed to get hand type,error code: {code}")
            elif result+self.address != 128:
                raise RuntimeError(f"Hand type mismatch,expected {128-self.address},got {result}")
                    
            return True
            
        except Exception as e:
            self.arm_controller.rm_delete_robot_arm()
            return False
        
    def _disconnect_device(self) -> bool:
        """
        断开与机械臂的连接
        :return: 是否成功断开连接
        """
        try:
            
            # 断开机械臂连接
            if self.arm_controller is not None and self.handle is not None:
                # 调用SDK接口断开连接
                self.arm_controller.rm_delete_robot_arm()
                self.handle = None
            
            print(f"[Disconnect] Robot arm disconnected from {self.ip}:{self.port}")
            return True
            
        except Exception as e:
            print(f"Error disconnecting robot arm: {str(e)}")
            return False
        
    def handle_openxr(self, hand_data: dict) -> list:
        """
        根据OpenXR手部骨架数据计算灵巧手控制值
        返回6个0-100的值，前五个表示手指弯曲程度，第六个表示大拇指向掌心收拢的程度
        
        Args:
            hand_data: OpenXR手部数据，包含joints数组和rootPose
            
        Returns:
            list: 6个0-100的值，分别对应拇指收拢、拇指弯曲、中指弯曲、食指弯曲、小指弯曲、无名指弯曲
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
            
            
            # 拇指弯曲程度 (thumb)
            # thumb_bend = calculate_finger_bend(
            #     joints[XR_HAND_JOINT_THUMB_METACARPAL_EXT],
            #     joints[XR_HAND_JOINT_THUMB_PROXIMAL_EXT],
            #     joints[XR_HAND_JOINT_THUMB_DISTAL_EXT],
            #     joints[XR_HAND_JOINT_THUMB_TIP_EXT]
            # )

            if 'fingers' in hand_data:
                index_bend = hand_data['fingers'][1]['fullCurl']*100
                middle_bend = hand_data['fingers'][2]['fullCurl']*100
                ring_bend = hand_data['fingers'][3]['fullCurl']*100
                little_bend = hand_data['fingers'][4]['fullCurl']*100
                thumb_bend = hand_data['fingers'][0]['fullCurl']*100
            else:
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
                thumb_bend = calculate_bone_bend(
                    joints[XR_HAND_JOINT_THUMB_METACARPAL_EXT],
                    joints[XR_HAND_JOINT_THUMB_PROXIMAL_EXT],
                    joints[XR_HAND_JOINT_THUMB_DISTAL_EXT]
                )

                index_bend = (index_bend-5)*2.5
                middle_bend = (middle_bend-5)*2.5
                ring_bend = (ring_bend-5)*2.5
                little_bend = (little_bend-5)*2.5
                thumb_bend = (thumb_bend-10)*2
            
            # 拇指收拢程度
            thumb_towards_palm = calculate_thumb_towards_palm(
                joints[XR_HAND_JOINT_WRIST_EXT],
                joints[XR_HAND_JOINT_PALM_EXT],
                joints[XR_HAND_JOINT_THUMB_METACARPAL_EXT],
                joints[XR_HAND_JOINT_THUMB_PROXIMAL_EXT],
                joints[XR_HAND_JOINT_THUMB_DISTAL_EXT]
            )
            thumb_towards_palm = (thumb_towards_palm-5)*1.5
            
            # 返回6个值：拇指收拢、拇指弯曲、中指弯曲、食指弯曲、小指弯曲、无名指弯曲
            thumb_towards_palm = max(0, min(100, int(thumb_towards_palm)))
            thumb_bend = max(0, min(100, int(thumb_bend)))
            middle_bend = max(0, min(100, int(middle_bend)))
            index_bend = max(0, min(100, int(index_bend)))
            little_bend = max(0, min(100, int(little_bend)))
            ring_bend = max(0, min(100, int(ring_bend)))
            return [thumb_towards_palm,thumb_bend,middle_bend, index_bend, little_bend, ring_bend]
            
        except Exception as e:
            # 如果计算过程中出现错误，返回默认值
            print(f"计算手部控制值时出错: {e}")
            return [50, 0, 0, 0, 0, 0]  # 拇指收拢程度默认为50
    def start_control(self):
        if not self.is_controlling:
            self.is_controlling = True
            self.control_thread_running = True
            
            # 启动控制线程
            self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
            self.control_thread.start()
            
            print("[Control] Control started.")
    
    def stop_control(self):
         if self.is_controlling:
            self.is_controlling = False
            self.control_thread_running = False
            
            # 等待控制线程结束
            if self.control_thread and self.control_thread.is_alive():
                self.control_thread.join(timeout=1.0)

            # 清空队列
            self.hand_queue.clear()
            
            print("[Control] Control stopped.")

    def _control_loop(self):
        while self.control_thread_running :
            if self._conn_status != 1:
                time.sleep(0.1)
                continue
            latest_data = None
            # 获取最新的数据，但不移除队列中的元素
            if len(self.hand_queue) > 0:
                latest_data = self.hand_queue[-1]  # 获取最新的数据（deque的最后一个元素）
            
            # 如果有新数据，则执行控制
            if latest_data is not None:
                self.fingers = self.set_fingers(latest_data)
            
            # 添加一个小延时以控制循环频率
            time.sleep(0.001)
