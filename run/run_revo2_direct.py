"""
本程序测试使用手柄扳机控制末端灵巧手和机械臂的效果
测试序列：张开 -> 闭合 -> 半开，每个状态保持2秒
利用VR手柄的扳机控制4指的弯曲度，控制灵巧手
"""
import asyncio
from EasyTeleop.Components import TeleopMiddleware, HandVisualizer
from EasyTeleop.Device.VR import VRSocket
from EasyTeleop.Device.Hand import Revo2Direct
import numpy as np
from EasyTeleop.Device.Hand.bc.revo2.revo2_utils import get_stark_port_name

# 为Revo2Direct类添加连接状态查询方法（也可直接在原类中实现）
def add_get_conn_status():
    if not hasattr(Revo2Direct, 'get_conn_status'):
        Revo2Direct.get_conn_status = lambda self: self.is_connected

add_get_conn_status()

# 一个人畜无害的测试代码
async def test_hand_control(left_hand, right_hand):
    """测试函数：循环发送张开/闭合指令"""
    # 等待设备初始化完成
    await asyncio.sleep(2)
    
    # 测试序列：张开 -> 闭合 -> 半开，每个状态保持2秒
    test_sequence = [
        [1000, 0, 0, 0, 0, 0],    # 完全张开
        [1000, 1000, 1000, 1000, 1000, 1000],  # 完全闭合
        [500, 500, 500, 500, 500, 500]         # 半开
    ]
    
    while True:
        for positions in test_sequence:
            # 同时控制左右手
            await left_hand.set_finger_positions(positions)
            await right_hand.set_finger_positions(positions)
            await asyncio.sleep(2)  # 每个动作保持2秒

async def main():
    try:
        print(get_stark_port_name())

        # 初始化设备
        r_hand = Revo2Direct({
            "port": "com3", 
            "slave_id": 0x7e,
            "control_fps": 80, 
            "hand_side": "left"
        }) 
        l_hand = Revo2Direct({
            "port": "com4", 
            "slave_id": 0x7f,
            "control_fps": 80, 
            "hand_side": "right"
        }) 
        vrsocket = VRSocket({"ip": '192.168.0.103', "port": 12345})
        teleop = TeleopMiddleware()
        
        devices = [r_hand, l_hand, vrsocket]
        
        # 注册回调函数
        @vrsocket.on("message")
        def teleop_handle_socket_data(message):
            if message['type'] == "hand":
                left_hand_values = [0, 0, 0, 0, 0, 0]
                right_hand_values = [0, 0, 0, 0, 0, 0]
                
                # 处理左手数据
                if 'leftHand' in message['payload'] and message['payload']['leftHand']['isTracked']:
                    left_hand_values = l_hand.handle_openxr(message['payload']['leftHand'])
                    if left_hand_values != [0, 0, 0, 0, 0, 0]:
                        l_hand.add_hand_data(left_hand_values)
                
                # 处理右手数据
                if 'rightHand' in message['payload'] and message['payload']['rightHand']['isTracked']:
                    right_hand_values = r_hand.handle_openxr(message['payload']['rightHand'])
                    if right_hand_values != [0, 0, 0, 0, 0, 0]:
                        r_hand.add_hand_data(right_hand_values)

            teleop.handle_socket_data(message)
        
        # 异步连接灵巧手
        await asyncio.gather(
            r_hand._connect_device(),
            l_hand._connect_device()
        )
        
        # 启动VRSocket（保持原有启动方式）
        vrsocket.start() 

        # 异步启动灵巧手控制
        await asyncio.gather(
            l_hand.start_control(),
            r_hand.start_control()
        )
        
        # 测试
        # asyncio.create_task(test_hand_control(l_hand, r_hand))

        # 监控设备状态
        while True:
            connect_states = [device.get_conn_status() for device in devices]
            print(f"设备连接状态: {connect_states}")
            await asyncio.sleep(1)  # 使用异步sleep

    except Exception as e:
        print(f"初始化失败: {e}")
        # 清理资源
        if 'r_hand' in locals():
            await r_hand._disconnect_device()
        if 'l_hand' in locals():
            await l_hand._disconnect_device()
        if 'vrsocket' in locals():
            vrsocket.stop()
        return

if __name__ == '__main__':
    asyncio.run(main())