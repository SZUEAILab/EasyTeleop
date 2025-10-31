"""
VR数据包分析器测试脚本
用于测试和分析VR设备的数据包帧率和帧间间隔
"""
import time
from EasyTeleop.Components.VRPacketAnalyzer import VRPacketAnalyzer
from EasyTeleop.Device.VR import VRSocket

if __name__ == "__main__":
    
    # 创建VR数据包分析器
    analyzer = VRPacketAnalyzer(max_points=500)
    
    vr_device = VRSocket({"ip": '192.168.0.103', "port": 12345})
    
    # 注册数据包接收回调
    @vr_device.on("message")
    def on_vr_message(data):
        # 将数据包添加到分析器
        print(time.time())
        if "payload" in data and "leftPos" in data['payload']:
            print(data['payload']['leftPos'])
            analyzer.add_packet(data)
        else:
            print(data)
        
    
    # 启动VR设备连接
    vr_device.start()
    
    # 在单独的线程中启动分析器
    analyzer.start(100)
    
    try:
        print("开始接收VR数据包（按Ctrl+C停止）...")
        # 保持主线程运行
        while True:
            print(vr_device.get_conn_status())
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n停止测试...")
    except Exception as e:
        print(f"\n发生错误: {e}")
    finally:
        # 断开设备连接
        vr_device.stop()
        # 停止分析器
        analyzer.stop()