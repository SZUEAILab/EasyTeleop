from ..BaseDevice import BaseDevice
from queue import Queue
class BaseVR(BaseDevice):
    def __init__(self, config):
        super().__init__(config)
        self.data_queue = Queue()
        self._events.update({
            "message": self._default_callback,#收到VR的数据包
        })
