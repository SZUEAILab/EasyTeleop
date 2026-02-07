import asyncio
import cv2
import logging
import threading
import queue
from av import VideoFrame
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, MediaStreamTrack, RTCIceCandidate
from aiortc.sdp import candidate_from_sdp, candidate_to_sdp
import websockets
import json

logger = logging.getLogger(__name__)
    
class VideoDisplayTrack(MediaStreamTrack):
    kind = "video"
    WINDOW_NAME = "Receiver View"

    def __init__(self, track):
        super().__init__()  # 初始化基类
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")
        cv2.imshow(self.WINDOW_NAME, img)
        cv2.waitKey(1)  # 不加这句 OpenCV 不刷新
        return frame


class CameraDeviceStreamTrack(VideoStreamTrack):
    """
    Video track that accepts frames from an external camera callback.
    """
    def __init__(self, queue_size=30):
        super().__init__()
        self._frame_queue = queue.Queue(maxsize=queue_size)
        self._lock = threading.Lock()

    def put_frame(self, color_frame):
        if color_frame is None:
            return
        if self._frame_queue.full():
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                pass
        try:
            self._frame_queue.put_nowait(color_frame)
        except queue.Full:
            pass

    async def recv(self):
        try:
            frame = self._frame_queue.get(timeout=5.0)
        except queue.Empty:
            raise Exception("Timeout waiting for camera frame")

        if frame is None:
            raise Exception("Received empty frame from camera")

        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts, video_frame.time_base = await self.next_timestamp()
        return video_frame

    def stop(self):
        with self._lock:
            while not self._frame_queue.empty():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    break
        super().stop()

class UnityWebRTC:
    def __init__(self, connection_id, signaling_url, reconnect_delay=3.0, max_reconnect_delay=10.0, frame_queue_size=30, offer_interval=5.0, enable_recv_display=False):
        self.connection_id = connection_id
        self.signaling_url = signaling_url
        self.ws = None
        self.pc = None
        self.pending_candidates = []
        self.should_run = True
        self._frame_queue_size = frame_queue_size
        self._track = None
        self._loop = None
        self._thread = None
        self._thread_lock = threading.Lock()
        self._conn_status = 0
        self._remote_connection_id = None
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_delay = max_reconnect_delay
        self._offer_interval = offer_interval
        self._offer_task = None
        self.polite = False
        self.enable_recv_display = enable_recv_display
        self._cleaning = False
        self._cleanup_lock = asyncio.Lock()
        self._display_track = None
        self._display_task = None
        self._rebuilding_offer = False
        self._restart_requested = False

    def start(self) -> bool:
        with self._thread_lock:
            if self._thread and self._thread.is_alive():
                return False
            self.should_run = True
            self._set_conn_status(2)
            self._thread = threading.Thread(target=self._thread_main, daemon=True)
            self._thread.start()
            return True

    def stop(self) -> bool:
        self.should_run = False
        self._set_conn_status(0)
        loop = self._loop
        if loop and loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self.cleanup(stop=True), loop)
            except Exception:
                pass
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        return True

    def get_conn_status(self) -> int:
        return self._conn_status

    def _set_conn_status(self, status: int) -> None:
        self._conn_status = status

    def _thread_main(self):
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.main_loop())
        finally:
            try:
                loop.run_until_complete(self.cleanup(stop=not self.should_run))
            except Exception:
                pass
            loop.close()
            self._loop = None

    def put_frame(self, frame):
        if self._track:
            self._track.put_frame(frame)

    async def main_loop(self):
        self.should_run = True
        delay = self._reconnect_delay
        while self.should_run:
            try:
                logger.info("Connecting to %s ...", self.signaling_url)
                await self.run_webrtc()
            except Exception as e:
                logger.error("Connection error: %s", e)
            if not self.should_run:
                break
            if self._restart_requested:
                delay = self._reconnect_delay
            logger.info("Reconnecting in %s seconds...", delay)
            await asyncio.sleep(delay)
            delay = min(self._max_reconnect_delay, delay + 1.0)

    async def run_webrtc(self):
        self._restart_requested = False
        self.ws = await websockets.connect(self.signaling_url, ping_interval=10, ping_timeout=10)
        logger.info("Connected to signaling server")
        self._set_conn_status(1)
        self._remote_connection_id = None
        self.polite = False
        await self._send_ws({
            "type": "connect",
            "connectionId": self.connection_id
        })

        try:
            while self.should_run:
                try:
                    raw = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                msg = json.loads(raw)
                msg_type = msg.get("type")

                if msg_type == "connect":
                    self.polite = msg.get("polite", False)
                    if not self.pc:
                        self._create_peer()
                    if not self.polite:
                        if self._offer_task is None or self._offer_task.done():
                            self._offer_task = asyncio.create_task(self._offer_loop())
                elif msg_type == "offer":
                    try:
                        await self._handle_offer(msg)
                    except Exception as e:
                        logger.error("Offer handling error: %s", e)
                elif msg_type == "answer":
                    try:
                        await self._handle_answer(msg)
                    except Exception as e:
                        logger.error("Answer handling error: %s", e)
                elif msg_type == "candidate":
                    try:
                        await self._handle_candidate(msg)
                    except Exception as e:
                        logger.error("Candidate handling error: %s", e)
                elif msg_type == "disconnect":
                    logger.warning("Disconnected")
                    self._set_conn_status(2)
                    break
                elif msg_type == "error":
                    logger.error("Signaling error: %s", msg.get("message"))
                    self._set_conn_status(2)
                    break
        except Exception as e:
            logger.error("WebRTC loop error: %s", e)
        finally:
            await asyncio.shield(self.cleanup(stop=False))

    def _create_peer(self):
        self.pc = RTCPeerConnection()
        pc = self.pc
        self.pending_candidates = []
        self._rebuilding_offer = False

        @pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate is None:
                return
            await self._send_candidate(candidate)

        @pc.on("connectionstatechange")
        async def on_connection_state_change():
            if pc is not self.pc:
                return
            state = pc.connectionState
            logger.info("Peer connection state: %s", state)
            if self._rebuilding_offer:
                return
            if state in ("failed", "disconnected", "closed"):
                self._set_conn_status(2)
                self._restart_requested = True

        @pc.on("track")
        def on_track(track):
            logger.info("Track received: %s", track.kind)
            if self.enable_recv_display and track.kind == "video":
                self._display_track = VideoDisplayTrack(track)
                self._display_task = asyncio.create_task(self._display_loop())

        self._track = CameraDeviceStreamTrack(queue_size=self._frame_queue_size)
        pc.addTrack(self._track)

    async def _display_loop(self):
        while True:
            try:
                await self._display_track.recv()
            except Exception as e:
                logger.info("Video stream ended: %s", e)
                break

    def _get_msg_connection_id(self, msg):
        msg_from = msg.get("from")
        if msg_from:
            return msg_from
        data = msg.get("data") or {}
        return data.get("connectionId") or self.connection_id

    def _get_outgoing_connection_id(self):
        return self._remote_connection_id or self.connection_id

    async def _handle_offer(self, msg):
        if not self.pc:
            self._create_peer()
        conn_id = self._get_msg_connection_id(msg)
        if self._remote_connection_id is None:
            self._remote_connection_id = conn_id
        elif conn_id != self._remote_connection_id:
            return
        if self.pc.signalingState != "stable":
            if not self.polite:
                logger.warning("Ignore offer in signaling state: %s", self.pc.signalingState)
                return
            logger.info("Rollback to accept offer in signaling state: %s", self.pc.signalingState)
            try:
                await self.pc.setLocalDescription(RTCSessionDescription(type="rollback", sdp=""))
            except Exception as e:
                logger.error("Rollback failed: %s", e)
            if self.pc.signalingState != "stable":
                logger.warning("Reset peer to accept offer in signaling state: %s", self.pc.signalingState)
                try:
                    await self.pc.close()
                except Exception:
                    pass
                self.pc = None
                self._rebuilding_offer = True
                self._create_peer()
            if not self.pc or self.pc.signalingState != "stable":
                return
        if not self.pc:
            return
        sdp = msg["data"]["sdp"]
        desc = RTCSessionDescription(sdp=sdp, type="offer")
        await self._handle_description(desc)
        self._rebuilding_offer = False

    async def _handle_answer(self, msg):
        if not self.pc:
            return
        conn_id = self._get_msg_connection_id(msg)
        if self._remote_connection_id and conn_id != self._remote_connection_id:
            return
        sdp = msg["data"]["sdp"]
        desc = RTCSessionDescription(sdp=sdp, type="answer")
        await self._handle_description(desc)

    async def _handle_description(self, desc):
        if desc.type == "answer" and self.pc.signalingState == "stable" and self.pc.remoteDescription and self.pc.remoteDescription.type == "answer":
            logger.info("Ignore duplicate answer in stable state")
            return

        try:
            await self.pc.setRemoteDescription(desc)
        except Exception as e:
            logger.error("SetRemoteDescription error: %s", e)
            return

        if desc.type == "offer":
            await self.pc.setLocalDescription(await self.pc.createAnswer())
            await self._send_answer()
            for candidate in self.pending_candidates:
                try:
                    await self.pc.addIceCandidate(candidate)
                except Exception:
                    pass
            self.pending_candidates.clear()

    async def _handle_candidate(self, msg):
        if not self.pc:
            return
        conn_id = self._get_msg_connection_id(msg)
        if self._remote_connection_id and conn_id != self._remote_connection_id:
            return
        data = msg.get("data") or {}
        candidate_sdp = data.get("candidate")
        if not candidate_sdp:
            return
        try:
            parsed = candidate_from_sdp(candidate_sdp)
        except Exception as e:
            logger.error("Invalid candidate: %s", e)
            return
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
            self.pending_candidates.append(candidate)
        else:
            try:
                await self.pc.addIceCandidate(candidate)
            except Exception:
                pass

    async def _send_offer(self):
        if not self.pc or not self.pc.localDescription:
            return
        await self._send_ws({
            "type": "offer",
            "from": self.connection_id,
            "data": {
                "sdp": self.pc.localDescription.sdp,
                "connectionId": self.connection_id
            }
        })

    async def _send_answer(self):
        if not self.pc or not self.pc.localDescription:
            return
        await self._send_ws({
            "type": "answer",
            "from": self.connection_id,
            "data": {
                "sdp": self.pc.localDescription.sdp,
                "connectionId": self._get_outgoing_connection_id()
            }
        })

    async def _send_candidate(self, candidate):
        try:
            candidate_sdp = candidate_to_sdp(candidate)
        except Exception as e:
            logger.error("Failed to encode candidate: %s", e)
            return
        await self._send_ws({
            "type": "candidate",
            "from": self.connection_id,
            "data": {
                "connectionId": self._get_outgoing_connection_id(),
                "candidate": candidate_sdp,
                "sdpMid": candidate.sdpMid,
                "sdpMLineIndex": candidate.sdpMLineIndex,
            }
        })

    async def _offer_loop(self):
        while self.should_run:
            await asyncio.sleep(self._offer_interval)
            if not self.pc or self.pc.signalingState != "stable":
                continue
            await self.pc.setLocalDescription(await self.pc.createOffer())
            await self._send_offer()

    async def cleanup(self, stop: bool = False):
        if self._cleaning:
            return
        self._cleaning = True
        async with self._cleanup_lock:
            if self._display_track:
                try:
                    self._display_track.stop()
                except Exception:
                    pass
                self._display_track = None
            if self._display_task:
                try:
                    self._display_task.cancel()
                    await asyncio.wait([self._display_task], timeout=0.5)
                except Exception:
                    pass
                self._display_task = None
            try:
                cv2.destroyWindow(VideoDisplayTrack.WINDOW_NAME)
            except Exception:
                pass
            if self._offer_task:
                self._offer_task.cancel()
                self._offer_task = None
            if self.pc:
                try:
                    await self.pc.close()
                except Exception:
                    pass
                self.pc = None
            if self._track:
                try:
                    self._track.stop()
                except Exception:
                    pass
                self._track = None
            if stop and self.ws:
                try:
                    await self.ws.send(json.dumps({
                        "type": "disconnect",
                        "connectionId": self.connection_id
                    }))
                except Exception:
                    pass
                self.ws = None
            self.pending_candidates.clear()
        self._cleaning = False

    async def _send_ws(self, payload):
        if not self.ws:
            return
        await self.ws.send(json.dumps(payload))
    
