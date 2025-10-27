#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
插值组件测试脚本
"""

import time
import numpy as np
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import TeleopMiddleware,Interpolation
from Device.VR.VRSocket import VRSocket
from Device.Robot.RealMan import RealMan

def main():
    print("开始插值组件测试...")
    
    try:
        interpolator = Interpolation(max_data_points=50, interpolation_rate=0.005)
        
        arm = RealMan({"ip": "192.168.0.17", "port": 8080})
        vrsocket = VRSocket({"ip": '192.168.0.103', "port": 12345})
        teleop = TeleopMiddleware()
        
        devices = [arm, vrsocket]
    except Exception as e:
        print(f"初始化组件时出错: {e}")
        return
    
    try:
        # 注册回调函数
        teleop.on("rightGripTurnDown",arm.start_control)
        teleop.on("rightGripTurnUp",arm.stop_control)
        @teleop.on("rightPosRot")
        def calculate_hand_values(pose_data):
            interpolator.add_pose_data(pose_data)
            # arm.add_pose_data(pose_data)

        @interpolator.on("pose")
        def control_arm(pose_data):
            
            if arm.is_controlling:
                if arm.prev_tech_state is None:
                    # 初始化状态
                    arm.prev_tech_state = pose_data
                    arm.arm_first_state = arm.get_pose()
                    arm.delta = [0, 0, 0, 0, 0, 0, 0]
                else:
                    arm.move(pose_data)
        teleop.on("rightTrigger",arm.add_end_effector_data)
        
        #注册回调函数
        vrsocket.on("message",teleop.handle_socket_data)

        arm.start()
        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响

        interpolator.start()
        
        while(1):
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            time.sleep(1)

        
        
    except KeyboardInterrupt:
        print("收到中断信号")
    finally:
        # 停止组件
        print("停止中...")
        interpolator.stop()
        arm.stop()
        vrsocket.stop()
        print("测试完成")

if __name__ == "__main__":
    main()