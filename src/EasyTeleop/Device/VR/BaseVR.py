from ..BaseDevice import BaseDevice
from queue import Queue, Empty
import threading

class BaseVR(BaseDevice):
    def __init__(self, config):
        super().__init__(config)
        self.data_queue = Queue()
        # 初始化两个队列用于存放反馈数据和视频帧
        self.feedback_queue = Queue()
        self.video_frame_queue = Queue()
        self._feedback_thread = None
        self._feedback_stop_event = threading.Event()
        self._events.update({
            "message": self._default_callback,#收到VR的数据包
        })
    
    # 提供向反馈队列压数据的接口
    def add_feedback_data(self, data):
        self.feedback_queue.put(data)
    
    # 提供向视频帧队列压数据的接口
    def add_video_frame(self, frame):
        self.video_frame_queue.put(frame)

    def start_feedback_loop(self):
        """启动反馈发送循环"""
        if self._feedback_thread and self._feedback_thread.is_alive():
            return
        self._feedback_stop_event.clear()
        self._feedback_thread = threading.Thread(target=self._feedback_loop, daemon=True)
        self._feedback_thread.start()

    def stop_feedback_loop(self):
        """停止反馈发送循环"""
        self._feedback_stop_event.set()
        if self._feedback_thread and self._feedback_thread.is_alive():
            self._feedback_thread.join(timeout=1.0)
        self._feedback_thread = None

    def set_conn_status(self, status: int) -> None:
        """
        扩展连接状态切换：进入连接状态时开启反馈线程，退出连接时关闭
        """
        prev_status = self.get_conn_status()
        super().set_conn_status(status)
        if status == 1 and prev_status != 1:
            self.start_feedback_loop()
        elif status != 1 and prev_status == 1:
            self.stop_feedback_loop()

    def _feedback_loop(self):
        """循环从队列取包并发送，异常时回退队列并触发重连"""
        while not self._feedback_stop_event.is_set():
            try:
                packet = self.feedback_queue.get(timeout=0.1)
            except Empty:
                continue
            try:
                if self.get_conn_status() != 1:
                    self.feedback_queue.put(packet)
                    break
                self._send_feedback(packet)
            except Exception as e:
                self.emit("error", f"反馈发送失败: {e}")
                self.feedback_queue.put(packet)
                self.set_conn_status(2)
                break

    def _send_feedback(self, packet):
        """
        发送反馈包的具体实现，由子类实现
        """
        raise NotImplementedError("子类需实现 _send_feedback")
