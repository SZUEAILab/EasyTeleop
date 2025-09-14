import threading
import queue
import time
import cv2
import os

class DataCollect:
    def __init__(self, video_dir="datasets/video", state_file="datasets/robot_states.txt"):
        self.video_queue = queue.Queue()
        self.state_queue = queue.Queue()
        self.running = False
        self.video_dir = video_dir
        self.state_file = state_file
        os.makedirs(self.video_dir, exist_ok=True)
        self.video_consumer_thread = None
        self.state_consumer_thread = None

    def put_video_frame(self, frame, ts=None):
        """向视频队列添加帧（frame为numpy数组），附带时间戳"""
        if ts is None:
            ts = time.time()
        self.video_queue.put((ts, frame))

    def put_robot_state(self, state, ts=None):
        """向机械臂状态队列添加状态（state为dict或list），附带时间戳"""
        if ts is None:
            ts = time.time()
        self.state_queue.put((ts, state))

    def start(self):
        """启动消费线程"""
        if not self.running:
            self.running = True
            # 启动两个独立的消费线程
            self.video_consumer_thread = threading.Thread(target=self._consume_video, daemon=True)
            self.state_consumer_thread = threading.Thread(target=self._consume_state, daemon=True)
            self.video_consumer_thread.start()
            self.state_consumer_thread.start()

    def stop(self):
        """停止消费线程"""
        self.running = False
        if self.video_consumer_thread:
            self.video_consumer_thread.join()
        if self.state_consumer_thread:
            self.state_consumer_thread.join()

    def _consume_video(self):
        """消费视频帧线程：不断取出视频队列头部数据并存储到本地"""
        while self.running:
            try:
                ts, frame = self.video_queue.get(timeout=0.1)
                filename = os.path.join(self.video_dir, f"frame_{ts:.3f}.jpg")
                cv2.imwrite(filename, frame)
                self.video_queue.task_done()
            except queue.Empty:
                pass

    def _consume_state(self):
        """消费机械臂状态线程：不断取出状态队列头部数据并存储到本地"""
        while self.running:
            try:
                ts, state = self.state_queue.get(timeout=0.1)
                with open(self.state_file, "a", encoding="utf-8") as f:
                    f.write(f"{ts:.3f}: {state}\n")
                self.state_queue.task_done()
            except queue.Empty:
                pass