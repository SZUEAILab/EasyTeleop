import asyncio
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack,MediaStreamTrack, RTCIceCandidate
from aiortc.sdp import candidate_from_sdp
import websockets
import json
    
class VideoDisplayTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, track):
        super().__init__()  # 初始化基类
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")
        cv2.imshow("📺 Receiver View", img)
        cv2.waitKey(1)  # 不加这句 OpenCV 不刷新
        return frame

class UnityWebRTC:
    def __init__(self, connection_id, signaling_url, tracker=None):
        self.connection_id = connection_id
        self.signaling_url = signaling_url
        self.ws = None
        self.pc = None
        self.pending_candidates = []
        self.should_run = True
        self.tracker = tracker
        self.waitingAnswer = False
        self.ignoreOffer = False

    async def connect(self):
        while self.should_run:
            try:
                print(f"🔗 Connecting to {self.signaling_url} ...")
                await self.run_webrtc()
            except Exception as e:
                print(f"⚠️ Connection error: {e}")
            print("⏳ Reconnecting in 3 seconds...")
            await asyncio.sleep(3)

    async def run_webrtc(self):
        self.ws = await websockets.connect(self.signaling_url)
        print("✅ Connected to signaling server")
        await self.ws.send(json.dumps({
            "type": "connect",
            "connectionId": self.connection_id
        }))
        self.pc = RTCPeerConnection()
        if self.tracker:
            self.pc.addTrack(self.tracker)
        self.pending_candidates = []

        # 连接成功后立即创建Offer并发送
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)

        self.waitingAnswer = True

        await self.ws.send(json.dumps({
            "type": "offer",
            "from": self.connection_id,
            'data': {
                "sdp": self.pc.localDescription.sdp,
                "sdpType": self.pc.localDescription.type,
                "connectionId": self.connection_id
            }
        }))

        print("📤have Sent Offer")

        async def handle_candidate(msg):
            parsed = candidate_from_sdp(msg['data']['candidate'])
            candidate = RTCIceCandidate(
                foundation=parsed.foundation,
                component=parsed.component,
                priority=parsed.priority,
                ip=parsed.ip,
                protocol=parsed.protocol,
                port=parsed.port,
                type=parsed.type,
                tcpType=parsed.tcpType,
                sdpMid=msg['data']["sdpMid"],
                sdpMLineIndex=msg['data']["sdpMLineIndex"]
            )

            if self.pc.remoteDescription is None:
                print("⏳ Remote description not set yet, queue candidate")
                self.pending_candidates.append(candidate)
            else:
                await self.pc.addIceCandidate(candidate)
                print("✅ Added ICE candidate immediately")

        async def handle_offer(msg):
            if self.ignoreOffer or self.waitingAnswer:
                print("⏳ Waiting for previous answer, ignoring this offer")
                return
            self.ignoreOffer = True
            sdp = msg["data"]["sdp"]
            print(f"📥 Received Offer")

            # self.pc = RTCPeerConnection()
            # self.pc.addTrack(self.tracker)
            await self.pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="offer"))

            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)

            await self.ws.send(json.dumps({
                "type": "answer",
                "from": self.connection_id,
                "data": {
                    "sdp": self.pc.localDescription.sdp,
                    "connectionId": self.connection_id
                }
            }))

            print("📤 Sent Answer")

            for candidate in self.pending_candidates:
                await self.pc.addIceCandidate(candidate)
            self.pending_candidates.clear()

        async def handle_answer(msg):
            self.waitingAnswer = False
            self.ignoreOffer = True
            sdp = msg["data"]["sdp"]
            print(f"📥 Received Answer")
            await self.pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="answer"))

            for candidate in self.pending_candidates:
                await self.pc.addIceCandidate(candidate)
            self.pending_candidates.clear()
            
        @self.pc.on("track")
        def on_track(track):
            print(f"🎥 Track received: {track.kind}")
            if track.kind == "video":
                display_track = VideoDisplayTrack(track)
                # 启动一个后台任务来保持接收画面
                asyncio.create_task(display_loop(display_track))

        async def display_loop(track):
            while True:
                try:
                    await track.recv()
                except Exception as e:
                    print("📴 Video stream ended:", e)
                    break

        try:
            while True:
                msg = json.loads(await self.ws.recv())
                msg_type = msg.get("type")

                if msg_type == "offer":
                    await handle_offer(msg)
                elif msg_type == "answer":
                    await handle_answer(msg)
                elif msg_type == "candidate":
                    await handle_candidate(msg)
                elif msg_type == "disconnect":
                    print("Disconnected")
                    break
        except Exception as e:
            print(f"⚠️ WebRTC loop error: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        if self.pc:
            await self.pc.close()
            self.pc = None
        if self.ws:
            await self.ws.close()
            self.ws = None

    def stop(self):
        self.should_run = False

if __name__ == "__main__":
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Device.Camera.RealSenseCamera import RealSenseCamera
    from StreamTracker import CameraDeviceStreamTrack
    camera_config = {
        "serial": "153122070447" ,
        "target_fps": 30
    }
    realsense_camera = RealSenseCamera(camera_config)
    tracker = CameraDeviceStreamTrack()
    
    realsense_camera.start()
    realsense_camera.on("frame",tracker.put_frame)
    client = UnityWebRTC(connection_id="LeftEye", signaling_url="wss://webrtc.chainpray.top",tracker=tracker)
    
    asyncio.run(client.connect())
    
    
    
    # Example usage: 传入自定义相机对象或使用默认相机
    # tracker1 = RealSenseStreamTrack(serial="153122070447")
    # tracker2 = RealSenseStreamTrack(serial="427622270438")
    # client1 = UnityWebRTC(connection_id="LeftEye", signaling_url="wss://webrtc.chainpray.top",tracker=tracker1)
    # client2 = UnityWebRTC(connection_id="RightEye", signaling_url="wss://webrtc.chainpray.top",tracker=tracker2)
    # client3 = UnityWebRTC(connection_id="MainView", signaling_url="wss://webrtc.chainpray.top")
    # async def main():
    #     # 并发运行多个 connect()
    #     await asyncio.gather(
    #         client1.connect(),
    #         client2.connect()
    #     )

    # try:
    #     asyncio.run(main())
    # except KeyboardInterrupt:
    #     print("🛑 Interrupted")
    
    
    # asyncio.run(client1.connect())