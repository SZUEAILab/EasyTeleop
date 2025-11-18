#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDS测试脚本 - 直接测试宇树G1机械臂状态订阅和控制功能
"""

import sys
import os
import time
from collections import deque

# 添加项目路径
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(os.path.abspath(project_root))
sys.path.append(os.path.join(os.path.abspath(project_root), 'src'))
sys.path.append(os.path.join(os.path.abspath(project_root), 'src', 'unitree_sdk2_python'))

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_, LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_, unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.utils.crc import CRC
import numpy as np
import threading

# 控制参数
control_dt = 1.0 / 250.0  # 250Hz控制频率
kp_low = 80.0
kd_low = 3.0
arm_velocity_limit = 20.0

# 宇树G1机械臂关节索引 (23自由度版本)
class G1_23_JointArmIndex:
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

class G1_23_JointIndex:
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

    # Right arm
    kRightShoulderPitch = 19
    kRightShoulderRoll = 20
    kRightShoulderYaw = 21
    kRightElbow = 22

# 全局变量
lowstate_data = None
lowstate_lock = threading.Lock()
control_thread = None
control_running = False
crc = CRC()
q_target = np.zeros(8)
tauff_target = np.zeros(8)
ctrl_lock = threading.Lock()

def lowstate_callback(msg: LowState_):
    """低状态消息回调函数"""
    global lowstate_data
    with lowstate_lock:
        lowstate_data = msg
    # print(f"接收到低状态消息:")
    # print(f"  时间戳: {msg.tick}")
    # print(f"  模式: {msg.mode_pr}")
    # print(f"  部分关节角度: {[msg.motor_state[i].q for i in range(min(10, len(msg.motor_state)))]}")
    # print("-" * 50)

def get_current_dual_arm_q():
    """获取当前手臂关节角度"""
    global lowstate_data
    with lowstate_lock:
        current_state = lowstate_data
    
    if current_state is not None:
        arm_q = []
        for joint_id in [G1_23_JointArmIndex.kLeftShoulderPitch,
                        G1_23_JointArmIndex.kLeftShoulderRoll,
                        G1_23_JointArmIndex.kLeftShoulderYaw,
                        G1_23_JointArmIndex.kLeftElbow,
                        G1_23_JointArmIndex.kRightShoulderPitch,
                        G1_23_JointArmIndex.kRightShoulderRoll,
                        G1_23_JointArmIndex.kRightShoulderYaw,
                        G1_23_JointArmIndex.kRightElbow]:
            arm_q.append(current_state.motor_state[joint_id].q)
        return np.array(arm_q)
    return np.zeros(8)

def clip_arm_q_target(target_q, velocity_limit):
    """限制手臂关节速度"""
    current_q = get_current_dual_arm_q()
    delta = target_q - current_q
    motion_scale = np.max(np.abs(delta)) / (velocity_limit * control_dt)
    clipped_arm_q_target = current_q + delta / max(motion_scale, 1.0)
    return clipped_arm_q_target

def ctrl_dual_arm(q_target_new, tauff_target_new):
    """设置手臂控制目标"""
    global q_target, tauff_target
    with ctrl_lock:
        q_target = q_target_new
        tauff_target = tauff_target_new

def control_loop():
    """控制循环函数"""
    global control_running, lowstate_data, q_target, tauff_target
    
    # 创建低命令发布者
    lowcmd_publisher = ChannelPublisher("rt/arm_sdk", LowCmd_)
    lowcmd_publisher.Init()
    
    # 初始化命令消息
    cmd_msg = unitree_hg_msg_dds__LowCmd_()
    cmd_msg.mode_pr = 0
    
    # 初始化所有电机
    for i in range(23):
        cmd_msg.motor_cmd[i].mode = 1  # 锁定模式
        cmd_msg.motor_cmd[i].kp = 0.0
        cmd_msg.motor_cmd[i].kd = 0.0
        cmd_msg.motor_cmd[i].q = 0.0
        cmd_msg.motor_cmd[i].dq = 0.0
        cmd_msg.motor_cmd[i].tau = 0.0
    
    # 设置手臂关节PID参数
    arm_indices = [G1_23_JointArmIndex.kLeftShoulderPitch,
                  G1_23_JointArmIndex.kLeftShoulderRoll,
                  G1_23_JointArmIndex.kLeftShoulderYaw,
                  G1_23_JointArmIndex.kLeftElbow,
                  G1_23_JointArmIndex.kRightShoulderPitch,
                  G1_23_JointArmIndex.kRightShoulderRoll,
                  G1_23_JointArmIndex.kRightShoulderYaw,
                  G1_23_JointArmIndex.kRightElbow]
    
    for joint_id in arm_indices:
        cmd_msg.motor_cmd[joint_id].kp = kp_low
        cmd_msg.motor_cmd[joint_id].kd = kd_low
    
    start_time = time.time()
    last_print_time = time.time()
    is_moving = False
    
    while control_running:
        loop_start_time = time.time()
        
        with lowstate_lock:
            current_state = lowstate_data
            
        if current_state is not None:
            # 获取控制目标
            with ctrl_lock:
                arm_q_target = q_target
                arm_tauff_target = tauff_target
            
            # 限制速度
            clipped_arm_q_target = clip_arm_q_target(arm_q_target, arm_velocity_limit)
            
            # 设置启用arm_sdk
            cmd_msg.motor_cmd[29].q = 1.0
            
            # 设置手臂关节控制参数
            for idx, joint_id in enumerate(arm_indices):
                cmd_msg.motor_cmd[joint_id].mode = 10  # 控制模式
                cmd_msg.motor_cmd[joint_id].q = clipped_arm_q_target[idx]
                cmd_msg.motor_cmd[joint_id].dq = 0.0
                cmd_msg.motor_cmd[joint_id].tau = arm_tauff_target[idx]
                cmd_msg.motor_cmd[joint_id].kp = kp_low
                cmd_msg.motor_cmd[joint_id].kd = kd_low
            
            # 计算并设置CRC校验码
            cmd_msg.crc = crc.Crc(cmd_msg)
            
            # 发布命令
            lowcmd_publisher.Write(cmd_msg)
            
            # 打印控制状态
            current_time = time.time()
            if current_time - last_print_time > 1.0:  # 每秒打印一次
                print(f"控制循环运行中... 目标角度: {[f'{q:.2f}' for q in clipped_arm_q_target]}")
                last_print_time = current_time
        
        # 精确控制循环频率
        loop_end_time = time.time()
        loop_elapsed = loop_end_time - loop_start_time
        sleep_time = max(0, control_dt - loop_elapsed)
        time.sleep(sleep_time)

def start_control():
    """启动控制线程"""
    global control_thread, control_running
    control_running = True
    control_thread = threading.Thread(target=control_loop)
    control_thread.daemon = True
    control_thread.start()
    print("控制线程已启动")

def stop_control():
    """停止控制线程"""
    global control_running
    control_running = False
    if control_thread:
        control_thread.join(timeout=1.0)
    print("控制线程已停止")

def main():
    """主函数"""
    global lowstate_data
    
    print("DDS测试 - 宇树G1机械臂状态订阅和控制")
    print("初始化DDS通道...")
    
    # 尝试多种网络接口初始化方式
    initialized = False
    network_interfaces = ["eth1"]
    
    for interface in network_interfaces:
        try:
            if interface:
                ChannelFactoryInitialize(0, interface)
                print(f"DDS通道初始化成功，使用网络接口: {interface}")
            initialized = True
            break
        except Exception as e:
            print(f"使用网络接口 {interface} 初始化失败: {e}")
            continue
    
    if not initialized:
        print("所有网络接口初始化都失败，程序退出")
        return
    
    try:
        # 创建低状态订阅者
        print("创建低状态订阅者...")
        lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        lowstate_subscriber.Init(lowstate_callback, 10)
        print("低状态订阅者创建成功")
        
        # 等待初始状态数据（设置超时）
        print("等待初始状态数据...")
        timeout = 5.0  # 5秒超时
        start_wait = time.time()
        while lowstate_data is None and (time.time() - start_wait) < timeout:
            time.sleep(0.1)
        
        if lowstate_data is None:
            print("警告: 未接收到初始状态数据，将继续执行控制")
            # 尝试打印一些调试信息
            print("尝试读取一次状态数据...")
            temp_data = lowstate_subscriber.Read()
            if temp_data:
                print("成功读取到状态数据")
                with lowstate_lock:
                    lowstate_data = temp_data
            else:
                print("仍然无法读取到状态数据")
        else:
            print("接收到初始状态数据")
        
        # 启动控制
        start_control()
        
        # 发送测试控制指令
        print("发送测试控制指令...")
        test_q = np.array([0.0, 0.2, 0.0, 0.3, 0.0, -0.2, 0.0, 0.3])
        ctrl_dual_arm(test_q, np.zeros(8))
        
        print("开始订阅低状态消息和控制...")
        print("按 Ctrl+C 停止订阅和控制")
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在停止...")
    except Exception as e:
        print(f"运行过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 停止控制
        stop_control()
        print("DDS测试结束")

if __name__ == "__main__":
    main()