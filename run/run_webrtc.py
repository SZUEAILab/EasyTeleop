from EasyTeleop.Components import TeleopMiddleware, DataCollect
from EasyTeleop.Device.VR import VRSocket
from EasyTeleop.Device.Robot import RealMan
from EasyTeleop.Device.Camera import RealSenseCamera
from EasyTeleop.Components.WebRTC import UnityWebRTC
import time

if __name__ == '__main__':
    try:
        RealSenseCamera.find_device()
        l_arm = RealMan({"ip": "192.168.0.18", "port": 8080})
        r_arm = RealMan({"ip": "192.168.0.19", "port": 8080})
        vrsocket = VRSocket({"ip": '192.168.0.20', "port": 12345})
        teleop = TeleopMiddleware()
        camera1 = RealSenseCamera({"serial":"427622270438","target_fps": 30}) 
        camera2 = RealSenseCamera({"serial":"427622270277","target_fps": 30}) 
        client1 = UnityWebRTC(connection_id="LeftEye", signaling_url="wss://webrtc.chainpray.top")
        client2 = UnityWebRTC(connection_id="RightEye", signaling_url="wss://webrtc.chainpray.top")
        
        devices = [l_arm, r_arm, vrsocket, camera1,camera2]
        
        def callback1(frame):
            # print("LeftEye")
            client1.put_frame(frame)
            
        def callback2(frame):
            # print("RightEye")
            client2.put_frame(frame)
    
        camera1.on("frame",callback1 )
        camera2.on("frame",callback2 )
        
        # 注册回调函数
        teleop.on("leftGripDown",l_arm.start_control)
        teleop.on("leftGripUp",l_arm.stop_control)
        teleop.on("rightGripDown",r_arm.start_control)
        teleop.on("rightGripUp",r_arm.stop_control)
        vrsocket.on("message",teleop.handle_socket_data)
        
        camera1.start()
        camera2.start()
        l_arm.start()
        r_arm.start()
        vrsocket.start() #启动数据接收线程,理论要在注册回调函数之后,但在前面启动也不影响
        try:
            client1.start()
            client2.start()
        except KeyboardInterrupt:
            print("Interrupted")

        try:
            while True:
                connect_states = [device.get_conn_status() for device in devices]
                print(f"Device connection status {connect_states}")
                # cv2.waitKey(1)
                time.sleep(1)
        except KeyboardInterrupt:
            print("Interrupted")
        finally:
            client1.stop()
            client2.stop()
            
    except Exception as e:
        print(f"初始化失败: {e}")
        exit(1)
