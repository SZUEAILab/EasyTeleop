from ..BaseDevice import BaseDevice

class BaseVR(BaseDevice):
    def __init__(self, config):
        super().__init__(config)

        self._events.update({
            "message": self._default_callback,# rgb图像
        })
