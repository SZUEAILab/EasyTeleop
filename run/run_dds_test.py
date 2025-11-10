#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDS测试脚本 - 直接测试宇树G1机械臂状态订阅功能
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

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_

def lowstate_callback(msg: LowState_):
    """低状态消息回调函数"""
    print(f"接收到低状态消息:")
    print(f"  时间戳: {msg.stamp}")
    print(f"  模式: {msg.mode}")
    print(f"  部分关节角度: {[msg.motor_state[i].q for i in range(min(10, len(msg.motor_state)))]}")
    print("-" * 50)

def main():
    """主函数"""
    print("DDS测试 - 宇树G1机械臂状态订阅")
    print("初始化DDS通道...")
    
    try:
        # 初始化通道工厂
        # 在Windows上使用实际的网络接口名称
        # 从命令"netsh interface show interface"的输出可以看到接口名称
        ChannelFactoryInitialize(0, "20")  # 对应Realtek PCIe GbE Family Controller
        print("DDS通道初始化成功")
    except Exception as e:
        print(f"DDS通道初始化失败: {e}")
        print("尝试使用其他可能的网络接口...")
        try:
            ChannelFactoryInitialize(0, "Realtek PCIe GbE Family Controller")
            print("DDS通道初始化成功")
        except Exception as e2:
            print(f"DDS通道初始化仍然失败: {e2}")
            print("尝试不指定网络接口...")
            try:
                ChannelFactoryInitialize(0)
                print("DDS通道初始化成功（使用默认网络接口）")
            except Exception as e3:
                print(f"DDS通道初始化仍然失败: {e3}")
                return
    
    try:
        # 创建低状态订阅者
        print("创建低状态订阅者...")
        lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        lowstate_subscriber.Init(lowstate_callback, 10)
        print("低状态订阅者创建成功")
        
        print("开始订阅低状态消息...")
        print("按 Ctrl+C 停止订阅")
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在停止...")
    except Exception as e:
        print(f"运行过程中发生错误: {e}")
    finally:
        print("DDS测试结束")

if __name__ == "__main__":
    main()