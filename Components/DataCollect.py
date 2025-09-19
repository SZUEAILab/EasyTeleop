import threading
import queue
import time
import cv2
import os
import csv

class DataCollect:
    def __init__(self, save_dir="datasets/temp"):
        self.video_queue = queue.Queue()
        self.state_queue = queue.Queue()
        self.running = False
        self.save_dir = save_dir
        self.capture_state = 0  # 0: not capturing, 1: capturing
        self.session_timestamp = None
        self.state_file = None
        self.video_dir = None
        os.makedirs(self.save_dir, exist_ok=True)
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

    def set_capture_state(self, state) -> bool:
        """设置采集状态"""
        if self.capture_state == state: return False
        self.toggle_capture_state()
        return True

    def get_capture_state(self):
        """获取采集状态"""
        return self.capture_state

    def toggle_capture_state(self):
        """切换采集状态"""
        if self.capture_state == 0:
            self._start_new_session()
            self.capture_state = 1
        else:
            self.capture_state = 0

    def _start_new_session(self):
        """开始新的采集会话，创建时间戳文件夹"""
        self.session_timestamp = time.strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(self.save_dir, self.session_timestamp)
        self.video_dir = os.path.join(session_dir, "frames")
        self.state_file = os.path.join(session_dir, "states.csv")
        
        os.makedirs(self.video_dir, exist_ok=True)
        
        # Create CSV file with header
        with open(self.state_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "state"])

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
                # Check capture state before saving
                if self.capture_state == 1 and self.video_dir:
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
                # Check capture state before saving
                if self.capture_state == 1 and self.state_file:
                    with open(self.state_file, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow([f"{ts:.3f}", str(state)])
                self.state_queue.task_done()
            except queue.Empty:
                pass