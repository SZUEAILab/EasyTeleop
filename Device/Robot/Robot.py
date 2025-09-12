from ..BaseDevice import BaseDevice
from typing import Dict, Any
class Robot(BaseDevice):
    """
    机器人控制基类，所有具体机器人控制器需继承并实现以下方法。

    方法说明：
    - 
    """
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)