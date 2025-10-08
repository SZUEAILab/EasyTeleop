from av import VideoFrame
import cv2
import numpy as np
from aiortc import VideoStreamTrack
import pyrealsense2 as rs
import threading
import queue

class CameraStreamTrack(VideoStreamTrack):
    def __init__(self, device_index):
        """
        camera: 需要实现get_frame()方法的对象，返回BGR格式的numpy数组。
        """
        super().__init__()
        self.camera = cv2.VideoCapture(device_index)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.camera.read()
        if not ret:
            raise Exception("Camera read failed")
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create VideoFrame for WebRTC
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

class RealSenseStreamTrack(VideoStreamTrack):
    @staticmethod
    def find_device():
        context = rs.context()
        devices = context.query_devices()
        # 打印设备信息
        print("可用的设备:")
        for i, device in enumerate(devices):
            print(f"{i}: {device.get_info(rs.camera_info.name)} - Serial: {device.get_info(rs.camera_info.serial_number)}")
    def __init__(self,serial = None):
        super().__init__()
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        if serial:
            self.config.enable_device(serial)  # Enable device by serial number
        self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        self.pipeline.start(self.config)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            raise Exception("RealSense camera read failed")

        # Convert RealSense frame to numpy array
        frame = np.asanyarray(color_frame.get_data())
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create VideoFrame for WebRTC
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

    def stop(self):
        self.pipeline.stop()

class CameraDeviceStreamTrack(VideoStreamTrack):
    """
    A VideoStreamTrack that wraps a RealSenseCamera device to provide frames for WebRTC
    """
    def __init__(self):
        """
        :param realsense_camera: An instance of RealSenseCamera from Device.Camera.RealSenseCamera
        """
        super().__init__()
        self._frame_queue = queue.Queue(maxsize=30)  # Limit queue size to prevent memory issues
        self._lock = threading.Lock()

    def put_frame(self, color_frame):
        """Callback when RealSenseCamera emits a frame"""
        if color_frame is not None:
            # Remove oldest frame if queue is full
            if self._frame_queue.full():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    pass
            # Add new frame to queue
            try:
                self._frame_queue.put_nowait(color_frame)
            except queue.Full:
                pass

    async def recv(self):
        """
        Receive the next video frame
        """
        # Get frame from queue with timeout
        try:
            frame = self._frame_queue.get(timeout=5.0)
        except queue.Empty:
            raise Exception("Timeout waiting for RealSense camera frame")
        
        if frame is None:
            raise Exception("Received empty frame from RealSense camera")
        
        # Convert BGR to RGB
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create VideoFrame for WebRTC
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts, video_frame.time_base = await self.next_timestamp()
        return video_frame

    def stop(self):
        """Stop the stream track"""
        # Clear the queue
        with self._lock:
            while not self._frame_queue.empty():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    break
        super().stop()