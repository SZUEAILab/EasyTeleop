# Device 模块文档

Device 模块是 EasyTeleop 系统中负责设备管理的核心模块。它提供了统一的设备接口，支持多种类型的设备，包括机械臂、VR 设备和摄像头等。

## BaseDevice 基类

所有设备的抽象基类，有如下三类业务逻辑：

### 事件驱动

所有设备采用事件驱动（event drive），当遇到 frame、state 等数据到达时使用 `self.emit` 触发注册好的事件，进行额外处理；注意通过 `on` 注册的回调函数需要是非阻塞的。

- `_event: Dict[str, Callable]` —— 维护的回调函数字典
- `_default_callback()`：默认的空回调函数
- `on(self, event_name: str, callback: Callable) -> bool`：注册事件回调

on 的回调注册提供传统函数式方法例如：`device.on("state", dc.push_state_queue)`，也可以使用下面的修饰器写法来注册：

```python
@camera1.on("frame")
def show_frame(frame):
    dc.put_video_frame(frame)
```

- `off(self, event_name: str) -> bool`：移除对应事件注册的回调
- `emit(self, event_name: str, *args, **kwargs) -> None`：触发事件

### Config 配置

- `__init__(self, config=None)`：可以选择在实例化对象的时候传入 config
- `need_config: Dict[str, Any]`：静态字段，定义设备所需的配置字段
- `get_need_config()`：静态方法，获取 need_config
- `set_config()`：传入 config 并验证是否满足 need_config 需要的字段，然后拆解并赋值对应的字段

### 连接状态

- `_conn_status`：连接状态，0=未连接(灰色)，1=已连接(绿色)，2=重连中(红色)，初始为 0
- `_main_loop()`：设备主循环，负责根据 _conn_status 执行对应方法
- `_main()`：设备核心处理逻辑，负责获取设备数据
- `start()`：多线程启动 _main_loop 并将 _conn_status 置为 2（2 会持续尝试 _connect_device）
- `stop()`：_conn_status 置为 0 并调用 _disconnect_device，等待 _main_loop 线程停止
- `_connect_device() -> bool`：在 _conn_status==2 的时候 _main_loop 会持续调用 _connect_device，直到 _connect_device 返回 True，将 _conn_status 置为 1 进入 _main 处理逻辑
- `_disconnect_device() -> bool`：stop 的时候会调用

关系转换图如下，start 后会在 12 之间切换状态，状态 2 需要持续尝试重连：

```
0 (未连接) --start()--> 2 (重连中) --_connect_device()成功--> 1 (已连接)
  ^                      |                                    |
  | stop()               | _connect_device()失败              | 正常运行或出错
  |                      v                                    v
  +------------------- 2 (重连中) <-- _main()出错或连接断开 -- 1 (已连接)
```

子类需要实现上方用黄色标出的 4 个抽象方法和配置一个静态字段 need_config：

- `set_config`
- `_main`
- `_connect_device`
- `_disconnect_device`

除此以外子类可以在 `_event` 中加入更多和自己相关的事件。

## 具体设备类型实现

### Robot 基类 (Device/Robot/BaseRobot.py)

机器人控制抽象基类，所有具体机器人控制器需继承并实现以下方法：

- `get_state()`：获取当前位姿（需启动轮询线程不断更新自身状态字段）。
- `get_gripper()`：获取当前夹爪状态。
- `start_control(state, trigger=None)`：启动控制，参数为目标位姿和夹爪开合度。
- `stop_control()`：停止控制。

状态获取通过轮询线程不断更新自身 `_state` 字段，`get_state` 直接返回该字段。

提供 `state` 回调接口，在轮询线程收到新数据后自动调用，用于自定义逻辑（如数据采集）。

### Camera 基类 (Device/Camera/BaseCamera.py)

- `_event` 增加 `frame` 事件，参数是 rgb 帧，用于摄像头接收到新的 frame 后触发

### VR 基类 (Device/VR/BaseVR.py)

- `_event` 增加 `message` 事件，用于接收到完整字典包后触发

### VRSocket 类 (Device/VR/VRSocket.py)

- 负责与 VR 头显的 TCP Server 建立连接，并启动接收线程。
- 持续接收 TCP 包，解析为 json 字典。
- 通过注册的回调函数（如 message），将数据传递给 Teleoperation 处理。

## 使用示例

```python
from Device.Robot.RealMan import RM_controller

# 创建配置
config = {
    'ip': '192.168.1.100',
    'port': 8080
}

# 创建机器人实例
robot = RM_controller(config)

# 注册回调
@robot.on("state")
def on_state(state):
    print(f"Robot state: {state}")

# 启动机器人
robot.start()

# 发送控制指令
robot.start_control([0, 0, 0, 0, 0, 0])

# 停止控制
robot.stop_control()

# 停止机器人
robot.stop()
```