#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
宇树G1机械臂23自由度版本运行示例
"""

import sys
import os
import time
import numpy as np


from EasyTeleop.Device.Robot.yushu import YushuG1Arm23DOF
from EasyTeleop.Components.TeleopMiddleware import TeleopMiddleware

def main():
    """主函数"""
    print("宇树G1机械臂23自由度版本运行示例")
    print("初始化设备...")
    
    # 创建23自由度版本的宇树G1机械臂实例
    robot_config = {
        "fps": 50,
        "motion_mode": True,
        "simulation_mode": False
    }
    
    robot = YushuG1Arm23DOF(config=robot_config)
    
    
    # 启动设备
    print("启动设备...")
    robot.start()
    
    # 等待设备连接
    print("等待设备连接...")
    timeout = 10  # 10秒超时
    start_time = time.time()
    
    while not robot.is_connected() and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if not robot.is_connected():
        print("设备连接超时")
        return
    
    print("设备已连接")
    
    # 示例：发送一些测试关节角度
    print("开始发送测试关节角度...")
    
    # 8个关节角度值：左臂4个(ShoulderPitch, ShoulderRoll, ShoulderYaw, Elbow)，右臂4个(ShoulderPitch, ShoulderRoll, ShoulderYaw, Elbow)
    test_poses = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # 初始位置
        [0.1, 0.1, 0.1, 0.1, -0.1, -0.1, -0.1, -0.1],  # 轻微移动
        [0.2, 0.2, 0.2, 0.2, -0.2, -0.2, -0.2, -0.2],  # 更大移动
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # 回到初始位置
    ]
    
    try:
        for i, pose in enumerate(test_poses):
            print(f"发送第 {i+1} 组关节角度: {pose}")
            robot.send_pose_data(pose)
            time.sleep(2)  # 每组姿势保持2秒
            
        print("测试完成")
        
        # 保持运行以观察设备状态
        print("按 Ctrl+C 停止程序")
        while True:
            # 获取当前关节状态
            current_state = robot.get_current_joint_state()
            print(f"当前关节状态: {current_state}")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在停止设备...")
    except Exception as e:
        print(f"运行过程中发生错误: {e}")
    finally:
        # 停止设备
        robot.stop()
        print("设备已停止")

if __name__ == "__main__":
    main()