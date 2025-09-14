核心类说明
注意以下模块主循环全都要放在多线程中运行，通过start()和stop()来启动和停止，因为主线程需要运行web服务
核心是BaseDevice及其继承的子类，简单的继承关系图如下
暂时无法在飞书文档外展示此内容
BaseDevice基类
所有设备的抽象基类，有如下三类业务逻辑
事件回调
- _event: Dict[str, Callable]——维护的回调函数字典
- _default_callback()：默认的空回调函数
- on(self, event_name: str, callback: Callable) -> bool:注册事件回调
- off(self, event_name: str) -> bool:移除对应事件注册的回调
- emit(self, event_name: str, *args, **kwargs) -> None:触发事件
Config配置
- need_config: Dict[str, Any] ，注意是静态字段放在init外面
- set_config():传入config并验证是否满足need_config需要的字段，然后拆解并赋值对应的字段
连接状态
- _conn_status：连接状态: 0=未连接(灰色), 1=已连接(绿色), 2=断开连接(红色)
- start()：根据config启动事件主循环
- stop()
关系转换图如下,start后会在12之间切换状态，状态2需要持续尝试重连
暂时无法在飞书文档外展示此内容
Robot基类 (Robot/BaseRobot.py)
- 机器人控制抽象基类，所有具体机器人控制器需继承并实现以下方法：
  - get_state()：获取当前位姿（需启动轮询线程不断更新自身状态字段）。
  - get_gripper()：获取当前夹爪状态。
  - start_control(state, trigger=None)：启动控制，参数为目标位姿和夹爪开合度。
  - stop_control()：停止控制。
- 状态获取通过轮询线程不断更新自身 _state 字段，get_state 直接返回该字段。
- 提供 on_state 回调接口，在轮询线程收到新数据后自动调用，用于自定义逻辑（如数据采集）。
VRSocket类 (VRSocket.py)
- 负责与VR头显的TCP Server建立连接，并启动接收线程。
- 持续接收TCP包，解析为json字典。
- 通过注册的回调函数（如 on_message），将数据传递给 Teleoperation 处理。
Teleoperation类 (Teleoperation.py)
- 负责处理 VRSocket 传递过来的json字典。
- 每个Key（如 buttonATurnDown）调用对应的回调函数，实现事件驱动。
- 支持注册自定义事件回调，实现遥操作逻辑。
DataCollect类 (DataCollect.py)
- 实现两个线程安全队列：视频帧队列和机械臂状态队列。
- put_video_frame(frame) 和 put_robot_state(state) 方法用于数据入队。
- start() 启动消费线程，不断从队列头部取出数据并存储到本地文件系统，带时间戳。
- 可用于采集和保存遥操作过程中的视频和状态数据。

数据通路
对于一个遥操进程（Teleoperation.py），数据管道如下
- VRSocket基类负责轮询从各种VR设备获取手臂数据帧并处理成标准格式
- Robot基类负责轮询获取机械臂当前状态并存储在自身字段
- 
对于数据采集，使用后处理思想，先全盘保存所有数据，再完成一次动作后拉起后处理进程后台处理
DataCollect类本身只负责
- Robot类自身维护一个线程安全的数据队列，轮询线程获取到新数据后入队
暂时无法在飞书文档外展示此内容