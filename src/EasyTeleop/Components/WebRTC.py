import asyncio
import cv2
import threading
import queue
from av import VideoFrame
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, MediaStreamTrack, RTCIceCandidate
from aiortc.sdp import candidate_from_sdp, candidate_to_sdp
import websockets
import json
    
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
    def __init__(self, connection_id, signaling_url, reconnect_delay=3.0, max_reconnect_delay=10.0, resend_interval=5.0, polite_offer_timeout=1.0, frame_queue_size=30):
        self.connection_id = connection_id
        self.signaling_url = signaling_url
        self.ws = None
        self.pc = None
        self.pending_candidates = []
        self.should_run = True
        self._frame_queue_size = frame_queue_size
        self._track = CameraDeviceStreamTrack(queue_size=frame_queue_size)
        self._loop = None
        self._thread = None
        self._thread_lock = threading.Lock()
        self._conn_status = 0
        self.polite = False
        self._making_offer = False
        self._waiting_answer = False
        self._ignore_offer = False
        self._srd_answer_pending = False
        self._remote_connection_id = None
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_delay = max_reconnect_delay
        self._resend_interval = resend_interval
        self._polite_offer_timeout = polite_offer_timeout
        self._resend_task = None
        self._initial_offer_task = None
        self._offer_fallback_task = None
        self._cleaning = False
        self._cleanup_lock = asyncio.Lock()
        self._received_offer = False
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
                asyncio.run_coroutine_threadsafe(self.cleanup(), loop)
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
            loop.run_until_complete(self._connect_loop())
        finally:
            try:
                loop.run_until_complete(self.cleanup())
            except Exception:
                pass
            loop.close()
            self._loop = None

    def put_frame(self, frame):
        if self._track:
            self._track.put_frame(frame)

    def _rebuild_track(self):
        if self._track:
            try:
                self._track.stop()
            except Exception:
                pass
        self._track = CameraDeviceStreamTrack(queue_size=self._frame_queue_size)

    def _reset_display(self):
        display_track = self._display_track
        display_task = self._display_task
        if display_track:
            try:
                display_track.close()
            except Exception:
                pass
            self._display_track = None
        if display_task:
            try:
                display_task.cancel()
            except Exception:
                pass
            self._display_task = None

    async def connect(self):
        self.should_run = True
        await self._connect_loop()

    async def _connect_loop(self):
        delay = self._reconnect_delay
        while self.should_run:
            try:
                print(f"Connecting to {self.signaling_url} ...")
                await self.run_webrtc()
            except Exception as e:
                print(f"Connection error: {e}")
            if not self.should_run:
                break
            if self._restart_requested:
                delay = self._reconnect_delay
            print(f"Reconnecting in {delay} seconds...")
            await asyncio.sleep(delay)
            delay = min(self._max_reconnect_delay, delay + 1.0)

    async def run_webrtc(self):
        self._restart_requested = False
        self.ws = await websockets.connect(self.signaling_url, ping_interval=10, ping_timeout=10)
        print("Connected to signaling server")
        self._set_conn_status(1)
        self._remote_connection_id = None
        self._received_offer = False
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
                        if self._initial_offer_task is None or self._initial_offer_task.done():
                            self._initial_offer_task = asyncio.create_task(self._force_initial_offer())
                elif msg_type == "offer":
                    try:
                        await self._handle_offer(msg)
                    except Exception as e:
                        print(f"Offer handling error: {e}")
                elif msg_type == "answer":
                    try:
                        await self._handle_answer(msg)
                    except Exception as e:
                        print(f"Answer handling error: {e}")
                elif msg_type == "candidate":
                    try:
                        await self._handle_candidate(msg)
                    except Exception as e:
                        print(f"Candidate handling error: {e}")
                elif msg_type == "disconnect":
                    print("Disconnected")
                    self._set_conn_status(2)
                    break
                elif msg_type == "error":
                    print(f"Signaling error: {msg.get('message')}")
                    self._set_conn_status(2)
                    break
        except Exception as e:
            print(f"WebRTC loop error: {e}")
        finally:
            await asyncio.shield(self.cleanup())

    def _create_peer(self):
        self._reset_display()
        self.pc = RTCPeerConnection()
        pc = self.pc
        self.pending_candidates = []
        self._making_offer = False
        self._waiting_answer = False
        self._ignore_offer = False
        self._srd_answer_pending = False
        self._received_offer = False
        self._rebuilding_offer = False

        @pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate is None:
                return
            await self._send_candidate(candidate)

        @pc.on("connectionstatechange")
        async def on_connection_state_change():
            state = pc.connectionState
            print(f"Peer connection state: {state}")
            if self._rebuilding_offer:
                return
            if state in ("failed", "disconnected", "closed"):
                self._set_conn_status(2)
                self._restart_requested = True
                try:
                    if self.ws:
                        await self.ws.close()
                except Exception:
                    pass

        @pc.on("negotiationneeded")
        async def on_negotiation_needed():
            if self._making_offer:
                return
            if pc.signalingState != "stable":
                return
            if self.polite:
                if self._offer_fallback_task is None or self._offer_fallback_task.done():
                    self._offer_fallback_task = asyncio.create_task(self._polite_offer_fallback(pc))
                return
            self._making_offer = True
            try:
                await pc.setLocalDescription(await pc.createOffer())
                self._waiting_answer = True
                await self._send_offer()
            finally:
                self._making_offer = False

        @pc.on("track")
        def on_track(track):
            print(f"Track received: {track.kind}")
            if track.kind == "video":
                display_track = VideoDisplayTrack(track)
                self._display_track = display_track
                self._display_task = asyncio.create_task(self._display_loop(display_track))

        if self._track:
            pc.addTrack(self._track)

        if self._resend_task:
            self._resend_task.cancel()
        self._resend_task = asyncio.create_task(self._resend_offer_loop())

    async def _display_loop(self, track):
        while True:
            try:
                await track.recv()
            except Exception as e:
                print("Video stream ended:", e)
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
        self._received_offer = True
        if self._offer_fallback_task and not self._offer_fallback_task.done():
            self._offer_fallback_task.cancel()
        conn_id = self._get_msg_connection_id(msg)
        if self._remote_connection_id is None:
            self._remote_connection_id = conn_id
        elif conn_id != self._remote_connection_id:
            return
        if self.pc.signalingState != "stable":
            if self.polite:
                print(f"Reset peer to accept offer in signaling state: {self.pc.signalingState}")
                try:
                    await self.pc.close()
                except Exception:
                    pass
                self.pc = None
                self._rebuilding_offer = True
                self._create_peer()
            else:
                print(f"Ignore offer in signaling state: {self.pc.signalingState}")
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
        is_stable = (
            self.pc.signalingState == "stable" or
            (self.pc.signalingState == "have-local-offer" and self._srd_answer_pending)
        )
        self._ignore_offer = (
            desc.type == "offer" and not self.polite and (self._making_offer or not is_stable)
        )
        if self._ignore_offer:
            print(f"Glare - ignoring offer in state {self.pc.signalingState}")
            return

        self._waiting_answer = False
        self._srd_answer_pending = desc.type == "answer"

        if desc.type == "answer" and self.pc.signalingState == "stable" and self.pc.remoteDescription and self.pc.remoteDescription.type == "answer":
            print("Ignore duplicate answer in stable state")
            return

        try:
            await self.pc.setRemoteDescription(desc)
        except Exception as e:
            print(f"SetRemoteDescription error: {e}")
            return
        self._srd_answer_pending = False

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
            print(f"Invalid candidate: {e}")
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
            print(f"Failed to encode candidate: {e}")
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

    async def _resend_offer_loop(self):
        while self.should_run:
            await asyncio.sleep(self._resend_interval)
            if not self.pc or not self._waiting_answer:
                continue
            if self.pc.localDescription and self.pc.localDescription.type == "offer":
                await self._send_offer()

    async def _polite_offer_fallback(self, pc):
        await asyncio.sleep(self._polite_offer_timeout)
        if not self.should_run or self._received_offer:
            return
        if pc.signalingState != "stable":
            return
        self._making_offer = True
        try:
            await pc.setLocalDescription(await pc.createOffer())
            self._waiting_answer = True
            await self._send_offer()
        finally:
            self._making_offer = False

    async def _force_initial_offer(self):
        await asyncio.sleep(0.1)
        if not self.should_run or not self.pc:
            return
        if self._waiting_answer or self.pc.signalingState != "stable":
            return
        self._making_offer = True
        try:
            await self.pc.setLocalDescription(await self.pc.createOffer())
            self._waiting_answer = True
            await self._send_offer()
        finally:
            self._making_offer = False

    async def cleanup(self):
        if self._cleaning:
            return
        self._cleaning = True
        async with self._cleanup_lock:
            display_track = self._display_track
            display_task = self._display_task if hasattr(self, "_display_task") else None
            if display_track:
                try:
                    display_track.close()
                except Exception:
                    pass
                self._display_track = None
            if display_task:
                try:
                    display_task.cancel()
                    await asyncio.wait([display_task], timeout=0.5)
                except Exception:
                    pass
                self._display_task = None
            try:
                cv2.destroyWindow(VideoDisplayTrack.WINDOW_NAME)
            except Exception:
                pass
            if self._resend_task:
                self._resend_task.cancel()
                self._resend_task = None
            if self._offer_fallback_task:
                self._offer_fallback_task.cancel()
                self._offer_fallback_task = None
            if self._initial_offer_task:
                self._initial_offer_task.cancel()
                self._initial_offer_task = None
            if self.pc:
                try:
                    await self.pc.close()
                    await asyncio.sleep(0)
                except Exception:
                    pass
                self.pc = None
            self._rebuild_track()
            if self.ws:
                try:
                    await self.ws.send(json.dumps({
                        "type": "disconnect",
                        "connectionId": self.connection_id
                    }))
                except Exception:
                    pass
                try:
                    await self.ws.close()
                except Exception:
                    pass
                self.ws = None
            self.pending_candidates.clear()
        self._cleaning = False

    async def _send_ws(self, payload):
        if not self.ws:
            return
        await self.ws.send(json.dumps(payload))
    
