# TeleopGroup 模块文档

TeleopGroup 是 EasyTeleop 系统中负责协调多个设备协同工作的模块。每个 TeleopGroup 实例代表一个完整的遥操作单元，包含机械臂、VR 设备和摄像头等设备，并负责它们之间的数据流转和协调控制。

## BaseTeleopGroup 基类

所有遥操组的抽象基类，定义了遥操组的基本结构和接口。

### 事件驱动

所有遥操组采用事件驱动（event drive），当遇到特定事件时使用 `self.emit` 触发注册好的事件，进行额外处理。注意通过 `on` 注册的回调函数需要是非阻塞的。

- `_event: Dict[str, Callable]` —— 维护的回调函数字典
- `_default_callback()`：默认的空回调函数
- `on(self, event_name: str, callback: Callable) -> bool`: 注册事件回调

on 的回调注册提供传统函数式方法例如：`teleop_group.on("start", logger)`, 也可以使用下面的修饰器写法来注册：

```python
@teleop_group.on("start")
def log_start():
    print("TeleopGroup started")
```

- `off(self, event_name: str) -> bool`: 移除对应事件注册的回调
- `emit(self, event_name: str, *args, **kwargs) -> None`: 触发事件

### 配置

- `__init__(self, config=None)`: 可以选择在实例化对象的时候传入 config
- `need_config: List[Dict[str, Any]]`，注意是静态字段放在 init 外面
- `get_info()`: 静态方法，获取包括 name、description 和 need_config 在内的完整信息
- `get_type_name()`: 静态方法，获取遥操组类型名称

### 生命周期管理

- `start() -> bool`: 启动遥操组，包括初始化设备、注册回调、启动数据采集等
- `stop() -> bool`: 停止遥操组，包括停止设备、清理回调、停止数据采集等

### 子类要求

子类需要实现以下抽象方法和配置静态字段：

1. `need_config` 静态字段：定义该遥操组类型所需的设备配置
2. `get_type_name()` 方法：返回遥操组类型的唯一标识
3. `start()` 方法：实现遥操组启动逻辑
4. `stop()` 方法：实现遥操组停止逻辑

## 具体遥操组类型实现

### DefaultTeleopGroup（默认遥操组）

支持双臂+VR+3摄像头的标准配置。

#### 配置需求

- left_arm：左臂设备（robot 类型）
- right_arm：右臂设备（robot 类型）
- vr：VR 设备（vr 类型）
- camera1：摄像头1（camera 类型）
- camera2：摄像头2（camera 类型）
- camera3：摄像头3（camera 类型）

#### 功能特点

- 支持双臂协同操作
- 通过 VR 设备进行姿态控制
- 支持最多 3 路摄像头视频流采集
- 提供完整的数据采集功能

## 使用示例

```python
from TeleopGroup.DefaultTeleopGroup import DefaultTeleopGroup

# 创建配置
config = [
    {
        'id': 1,
        'category': 'robot',
        'type': 'RealMan',
        'config': {'ip': '192.168.1.100', 'port': 8080}
    },
    {
        'id': 2,
        'category': 'vr',
        'type': 'Quest',
        'config': {'ip': '192.168.1.101', 'port': 9090}
    },
    {
        'id': 3,
        'category': 'camera',
        'type': 'RealSense',
        'config': {'camera_type': 'D435', 'camera_serial': '123456789'}
    }
]

# 创建遥操组实例
teleop_group = DefaultTeleopGroup(config)

# 注册回调
@teleop_group.on("start")
def on_start():
    print("遥操组已启动")

# 启动遥操组
teleop_group.start()

# 停止遥操组
teleop_group.stop()
```