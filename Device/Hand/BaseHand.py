from ..BaseDevice import BaseDevice

class BaseHand(BaseDevice):
    def __init__(self, config):
        super().__init__(config)

        self._events.update({
            "state": self._default_callback,#机械手状态，List
        })