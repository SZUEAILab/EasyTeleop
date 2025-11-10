from .BaseRobot import BaseRobot
import numpy as np
import threading
import time
from collections import deque
from enum import IntEnum
import logging

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize # dds
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import ( LowCmd_  as hg_LowCmd, LowState_ as hg_LowState) # idl for g1, h1_2
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.utils.crc import CRC

# 使用标准logging模块
logger = logging.getLogger(__name__)

class MotorState:
    def __init__(self):
        self.q = None
        self.dq = None

class G1_29_LowState:
    def __init__(self):
        self.motor_state = [MotorState() for _ in range(35)]  # G1_29_Num_Motors = 35

class DataBuffer:
    def __init__(self):
        self.data = None
        self.lock = threading.Lock()

    def GetData(self):
        with self.lock:
            return self.data

    def SetData(self, data):
        with self.lock:
            self.data = data

class G1_29_JointIndex(IntEnum):
    # Left leg
    kLeftHipPitch = 0
    kLeftHipRoll = 1
    kLeftHipYaw = 2
    kLeftKnee = 3
    kLeftAnklePitch = 4
    kLeftAnkleRoll = 5

    # Right leg
    kRightHipPitch = 6
    kRightHipRoll = 7
    kRightHipYaw = 8
    kRightKnee = 9
    kRightAnklePitch = 10
    kRightAnkleRoll = 11

    kWaistYaw = 12
    kWaistRoll = 13
    kWaistPitch = 14

    # Left arm
    kLeftShoulderPitch = 15
    kLeftShoulderRoll = 16
    kLeftShoulderYaw = 17
    kLeftElbow = 18
    kLeftWristRoll = 19
    kLeftWristPitch = 20
    kLeftWristyaw = 21

    # Right arm
    kRightShoulderPitch = 22
    kRightShoulderRoll = 23
    kRightShoulderYaw = 24
    kRightElbow = 25
    kRightWristRoll = 26
    kRightWristPitch = 27
    kRightWristYaw = 28
    
    # not used
    kNotUsedJoint0 = 29
    kNotUsedJoint1 = 30
    kNotUsedJoint2 = 31
    kNotUsedJoint3 = 32
    kNotUsedJoint4 = 33
    kNotUsedJoint5 = 34

class G1_29_JointArmIndex(IntEnum):
    # Left arm
    kLeftShoulderPitch = 15
    kLeftShoulderRoll = 16
    kLeftShoulderYaw = 17
    kLeftElbow = 18
    kLeftWristRoll = 19
    kLeftWristPitch = 20
    kLeftWristyaw = 21

    # Right arm
    kRightShoulderPitch = 22
    kRightShoulderRoll = 23
    kRightShoulderYaw = 24
    kRightElbow = 25
    kRightWristRoll = 26
    kRightWristPitch = 27
    kRightWristYaw = 28

# 为23自由度版本定义新的关节索引枚举
class G1_23_JointIndex(IntEnum):
    # Left leg
    kLeftHipPitch = 0
    kLeftHipRoll = 1
    kLeftHipYaw = 2
    kLeftKnee = 3
    kLeftAnklePitch = 4
    kLeftAnkleRoll = 5

    # Right leg
    kRightHipPitch = 6
    kRightHipRoll = 7
    kRightHipYaw = 8
    kRightKnee = 9
    kRightAnklePitch = 10
    kRightAnkleRoll = 11

    kWaistYaw = 12
    kWaistRoll = 13
    kWaistPitch = 14

    # Left arm (简化版，没有手腕关节)
    kLeftShoulderPitch = 15
    kLeftShoulderRoll = 16
    kLeftShoulderYaw = 17
    kLeftElbow = 18

    # Right arm (简化版，没有手腕关节)
    kRightShoulderPitch = 19
    kRightShoulderRoll = 20
    kRightShoulderYaw = 21
    kRightElbow = 22

class G1_23_JointArmIndex(IntEnum):
    # Left arm
    kLeftShoulderPitch = 15
    kLeftShoulderRoll = 16
    kLeftShoulderYaw = 17
    kLeftElbow = 18

    # Right arm
    kRightShoulderPitch = 19
    kRightShoulderRoll = 20
    kRightShoulderYaw = 21
    kRightElbow = 22

class YushuG1Arm23DOF(BaseRobot):
    """
    宇树G1机械臂设备类(23自由度版本)，继承自BaseRobot。
    实现与宇树G1机械臂的连接、控制和状态管理。
    """
    name = "Yushu G1 Arm 23DOF"
    description = "宇树G1双臂机械臂控制设备(23自由度版本)"
    
    need_config = {
        "fps": "控制频率，单位Hz",
        "motion_mode": "是否为运动模式",
        "simulation_mode": "是否为仿真模式"
    }
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        
        # 初始化配置
        if config:
            self.set_config(config)
        
        # 从unitree代码中提取的常量
        self.G1_23_Num_Motors = 23
        self.kTopicLowCommand_Debug  = "rt/lowcmd"
        self.kTopicLowCommand_Motion = "rt/arm_sdk"
        self.kTopicLowState = "rt/lowstate"
        
        # 控制参数
        self.kp_high = 300.0
        self.kd_high = 3.0
        self.kp_low = 80.0
        self.kd_low = 3.0
        self.arm_velocity_limit = 20.0
        self.control_dt = 1.0 / 250.0
        
        # 状态变量 (23自由度版本只需要8个关节值)
        self.q_target = np.zeros(8)
        self.tauff_target = np.zeros(8)
        self.all_motor_q = None
        
        # DDS通信相关
        self.lowcmd_publisher = None
        self.lowstate_subscriber = None
        self.lowstate_buffer = DataBuffer()
        self.crc = CRC()
        self.msg = None  # 初始化为None，稍后在_connect_device中正确初始化
        
        # 线程
        self.subscribe_thread = None
        self.publish_thread = None
        self.ctrl_lock = threading.Lock()
        self.data_lock = threading.Lock()
        
        # 数据队列
        self.pose_queue = deque(maxlen=10)
        
        # 标志位
        self._speed_gradual_max = False
        self._gradual_start_time = None
        self._gradual_time = None
        
        # 控制线程运行标志
        self.control_thread_running = False
        
        # 控制状态
        self.is_controlling = False
    
    def set_config(self, config: dict) -> bool:
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
        return True
        
    def _connect_device(self) -> bool:
        """连接宇树G1机械臂设备(23自由度版本)"""
        try:
            logger.info("正在连接宇树G1机械臂(23自由度版本)...")
            
            # 初始化ChannelFactory
            ChannelFactoryInitialize(0)  # TODO: 网络接口可能需要配置
            
            # 创建发布者和订阅者
            self.lowcmd_publisher = ChannelPublisher(self.kTopicLowCommand_Motion, hg_LowCmd)
            self.lowcmd_publisher.Init()
            
            self.lowstate_subscriber = ChannelSubscriber(self.kTopicLowState, hg_LowState)
            self.lowstate_subscriber.Init()
            
            # 正确初始化消息对象
            self.msg = unitree_hg_msg_dds__LowCmd_()
            
            # 启动订阅线程
            self.subscribe_thread = threading.Thread(target=self._subscribe_motor_state)
            self.subscribe_thread.daemon = True
            self.subscribe_thread.start()
            
            # 启动控制线程
            self.control_thread_running = True
            self.publish_thread = threading.Thread(target=self._ctrl_motor_state)
            self.publish_thread.daemon = True
            self.publish_thread.start()
            
            logger.info("宇树G1机械臂(23自由度版本)连接成功")
            return True
            
        except Exception as e:
            logger.error(f"连接宇树G1机械臂失败: {str(e)}")
            return False

    def _disconnect_device(self) -> bool:
        """断开宇树G1机械臂设备连接"""
        try:
            logger.info("正在断开宇树G1机械臂连接...")
            
            # 停止控制线程
            self.control_thread_running = False
            
            # 等待线程结束
            if self.publish_thread and self.publish_thread.is_alive():
                self.publish_thread.join(timeout=1.0)
                
            if self.subscribe_thread and self.subscribe_thread.is_alive():
                self.subscribe_thread.join(timeout=1.0)
            
            logger.info("宇树G1机械臂已断开连接")
            return True
            
        except Exception as e:
            logger.error(f"断开宇树G1机械臂连接失败: {str(e)}")
            return False
    
    def _main(self):
        """主循环逻辑，由BaseDevice管理"""
        if self.pose_queue:
            # 获取最新姿态数据（保留最新）
            with self.data_lock:
                pose_data = self.pose_queue[-1]  # 只取最新一帧
                self.pose_queue.clear()  # 清空队列，只保留最新
            
            # 解析目标关节角度 (23自由度版本只需要8个关节值)
            target_q = np.array(pose_data[:8])
            
            # 发送到机械臂控制器
            self.ctrl_dual_arm(target_q, np.zeros(8))  # 暂时不发送力矩
    
    def start_control(self) -> None:
        """开始控制机器人"""
        self.is_controlling = True
    
    def stop_control(self) -> None:
        """停止控制机器人"""
        self.is_controlling = False
    
    def get_current_motor_q(self):
        '''获取所有身体电机的当前状态q'''
        return np.array([self.lowstate_buffer.GetData().motor_state[id].q for id in G1_23_JointIndex])
    
    def get_current_dual_arm_q(self):
        '''获取左右臂电机的当前状态q'''
        lowstate_data = self.lowstate_buffer.GetData()
        if lowstate_data is None or lowstate_data.motor_state is None:
            # 如果没有接收到状态数据，返回零数组
            return np.zeros(len(G1_23_JointArmIndex))
        return np.array([lowstate_data.motor_state[id].q for id in G1_23_JointArmIndex])
    
    def ctrl_dual_arm(self, q_target, tauff_target):
        '''设置左右臂电机的控制目标值q & tau'''
        with self.ctrl_lock:
            self.q_target = q_target
            self.tauff_target = tauff_target
    
    def _Is_weak_motor(self, motor_index):
        weak_motors = [
            G1_23_JointIndex.kLeftAnklePitch.value,
            G1_23_JointIndex.kRightAnklePitch.value,
            # Left arm
            G1_23_JointIndex.kLeftShoulderPitch.value,
            G1_23_JointIndex.kLeftShoulderRoll.value,
            G1_23_JointIndex.kLeftShoulderYaw.value,
            G1_23_JointIndex.kLeftElbow.value,
            # Right arm
            G1_23_JointIndex.kRightShoulderPitch.value,
            G1_23_JointIndex.kRightShoulderRoll.value,
            G1_23_JointIndex.kRightShoulderYaw.value,
            G1_23_JointIndex.kRightElbow.value,
        ]
        return motor_index.value in weak_motors

    def _subscribe_motor_state(self):
        while self.control_thread_running:
            msg = self.lowstate_subscriber.Read()
            if msg is not None:
                lowstate = G1_23_LowState()
                for id in range(self.G1_23_Num_Motors):
                    lowstate.motor_state[id].q  = msg.motor_state[id].q
                    lowstate.motor_state[id].dq = msg.motor_state[id].dq
                self.lowstate_buffer.SetData(lowstate)
            time.sleep(0.002)
    
    def _ctrl_motor_state(self):
        if self.config["motion_mode"]:
            # 23自由度版本没有未使用的关节，所以这里留空或者根据需要调整
            pass

        while self.control_thread_running:
            # 确保消息对象已初始化
            if self.msg is None:
                time.sleep(0.002)
                continue
                
            start_time = time.time()

            with self.ctrl_lock:
                arm_q_target     = self.q_target
                arm_tauff_target = self.tauff_target

            # 限制速度
            cliped_arm_q_target = self.clip_arm_q_target(arm_q_target, velocity_limit = self.arm_velocity_limit)

            for idx, id in enumerate(G1_23_JointArmIndex):
                self.msg.motor_cmd[id].q = cliped_arm_q_target[idx]
                self.msg.motor_cmd[id].dq = 0
                self.msg.motor_cmd[id].tau = arm_tauff_target[idx]      

            self.msg.crc = self.crc.Crc(self.msg)
            self.lowcmd_publisher.Write(self.msg)

            if self._speed_gradual_max is True:
                t_elapsed = start_time - self._gradual_start_time
                self.arm_velocity_limit = 20.0 + (10.0 * min(1.0, t_elapsed / 5.0))

            current_time = time.time()
            all_t_elapsed = current_time - start_time
            sleep_time = max(0, (self.control_dt - all_t_elapsed))
            time.sleep(sleep_time)

    def clip_arm_q_target(self, target_q, velocity_limit):
        current_q = self.get_current_dual_arm_q()
        # 检查current_q是否有效
        if np.all(current_q == 0) and self.lowstate_buffer.GetData() is None:
            # 如果current_q全为0且没有接收到状态数据，则直接返回目标值
            return target_q
        delta = target_q - current_q
        motion_scale = np.max(np.abs(delta)) / (velocity_limit * self.control_dt)
        cliped_arm_q_target = current_q + delta / max(motion_scale, 1.0)
        return cliped_arm_q_target

    def send_pose_data(self, pose_data: list):
        """接收姿态数据并添加到队列中"""
        with self.data_lock:
            self.pose_queue.append(pose_data)

    def get_current_joint_state(self) -> list:
        """获取当前关节状态"""
        if self.lowstate_buffer and self.lowstate_buffer.GetData():
            return self.get_current_dual_arm_q().tolist()
        return []
    
    def is_connected(self) -> bool:
        """检查设备是否已连接"""
        return self.get_conn_status() == 1