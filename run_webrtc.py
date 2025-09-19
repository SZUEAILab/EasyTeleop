from Components import TeleopMiddleware, DataCollect
from Device.VR.VRSocket import VRSocket
from Device.Robot.RealMan import RM_controller
from Device.Camera.RealSenseCamera import RealSenseCamera
from WebRTC.StreamTracker import CameraDeviceStreamTrack
from WebRTC.WebRTC import UnityWebRTC
import time
import asyncio

if __name__ == '__main__':
    try:
        l_arm = RM_controller({"ip": "192.168.0.18", "port": 8080})
        r_arm = RM_controller({"ip": "192.168.0.19", "port": 8080})
        vrsocket = VRSocket({"ip": '192.168.0.20', "port": 12345})
        teleop = TeleopMiddleware()
        camera1 = RealSenseCamera({"serial":"153122070447","target_fps": 30}) 
        camera2 = RealSenseCamera({"serial":"153122070447","target_fps": 30}) 
        tracker1 = CameraDeviceStreamTrack()
        tracker2 = CameraDeviceStreamTrack()
        client1 = UnityWebRTC(connection_id="LeftEye", signaling_url="wss://webrtc.chainpray.top",tracker=tracker1)
        client2 = UnityWebRTC(connection_id="RightEye", signaling_url="wss://webrtc.chainpray.top",tracker=tracker2)
        
        devices = [l_arm, r_arm, vrsocket, camera1]
    
        camera1.on("frame",tracker1.put_frame )
        camera2.on("frame",tracker2.put_frame )
        
        # 注册回调函数
        teleop.on("leftGripDown",l_arm.start_control)
        teleop.on("leftGripUp",l_arm.stop_control)
        teleop.on("rightGripDown",r_arm.start_control)
        teleop.on("rightGripUp",r_arm.stop_control)
        vrsocket.on("message",teleop.handle_socket_data)
        
        camera1.start()
        l_arm.start()
        r_arm.start()
        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响
        
        async def main():
            # 并发运行多个 connect()
            await asyncio.gather(
                client1.connect(),
                client2.connect(),
                # print(f"设备连接状态: {[device.get_conn_status() for device in devices]}")
            )

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("🛑 Interrupted")
            
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)


        
        
        
        
        
        
        asyncio.run(client.connect())