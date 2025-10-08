基本概念
- Node:每个数据盒子上运行的python代码称之为Node，Node会和后端建立双向连接
- Device：VR头显，机械臂，摄像头等等遥操的设备
- TeleopGroup：遥操组，也就是将上面的一部分设备结合起来进行控制的最小单元
基本原则
1.后端和Node需要是无状态的
不要将重要配置和信息保存在内存变量中，比如：
- Node状态写入数据库
- Device状态通过MQTT同步
这样防止后端突然宕机之后丢失Node状态以及方便后续横向扩容
2.每个模块可横向扩容
和第一点说的差不多
3.Python不同模块解耦
详细参考Node数据通路和模块设计（python）
重点是使用成熟的中间件进行通信方便维护
4.良好的数据同步机制
python的Node和后端的配置数据要实现良好的同步
远期规划架构
暂时无法在飞书文档外展示此内容

近期实现架构
整体概览
暂时无法在飞书文档外展示此内容
1. 使用Go作为主后端服务，负责管理多个Python节点
2. Python节点负责与实际设备通信和控制
3. 通过WebSocket实现Go后端与Python节点之间的通信
4. 添加数据库来维护Python节点信息和设备信息
5. 支持同时在Go后端和Python节点上配置设备和遥操组，二者之间会同步信息并将设备注册到数据库

后端
- 维护数据库以存储节点、设备和遥操作组信息
- 提供RESTful API接口
- 维护WebSocket连接池，接受Node通过/ws/rpc路由的连接
- 通过JSON-RPC与Node通信，调用Node的方法，包括：
  - 开始与结束遥操组
  - 测试设备可用性

Python Node
数据盒子，通过网线/WIFI接入公网，主要负责：
- 有线连接摄像头
- 和机械臂做局域网通信
- 通过Modbus协议控制灵巧手
- 通过WebRCT直连/WebSocket转发等方式连接头显
设备拥有一个唯一标志uuidv4，会在程序首次启动时生成并储存在本地
Node不需要维护数据库，所有数据即时从后端获取
上线流程
1. 首先发送POST /api/node的请求，尝试注册
2. 接收上一步返回的devices和teleop-groups，初始化设备池和遥操组池
3. 注册成功通过websocket连接后端
遥操流程
1. 收到启动遥操的JSON-RPC包或者HTTP请求后根据遥操组的id实例化遥操组的python类
2. 根据config在内存中索引对应的设备配置并实例化
3. 按照指定逻辑注册好event_drive的回调函数
4. 注册好status_change的回调向MQTT上报Device状态的改变
MQTT维护状态
数据盒子节点将Node,TeleopGroup和Device的状态都上报MQTT服务器，前端直接向MQTT订阅状态
详细设计见MQTT话题设计
WebSocket协议设计
后端与数据盒子Node通信的手段，路由为/ws/rpc，其中的数据包遵循JSON-RPC 2.0基本格式
接口协议参考JSON-RPC API文档