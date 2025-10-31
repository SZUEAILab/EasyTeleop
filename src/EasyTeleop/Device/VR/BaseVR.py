from ..BaseDevice import BaseDevice
from queue import Queue

class BaseVR(BaseDevice):
    def __init__(self, config):
        super().__init__(config)
        self.data_queue = Queue()
        # 初始化两个队列用于存放反馈数据和视频帧
        self.feedback_queue = Queue()
        self.video_frame_queue = Queue()
        self._events.update({
            "message": self._default_callback,#收到VR的数据包
        })
    
    # 提供向反馈队列压数据的接口
    def add_feedback_data(self, data):
        self.feedback_queue.put(data)
    
    # 提供向视频帧队列压数据的接口
    def add_video_frame(self, frame):
        self.video_frame_queue.put(frame)