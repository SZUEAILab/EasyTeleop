# RealMan Teleoperate System

RealMan Teleoperate System 是一个基于VR设备控制机械臂的遥操作系统。该系统支持多种设备的集成，包括RealMan机械臂、VR头显和RealSense摄像头，并提供Web界面进行设备管理和遥操作控制。

## 功能特性

- 多设备管理：支持机械臂、VR头显和摄像头设备的统一管理
- Web界面控制：提供直观的Web界面进行设备配置和状态监控
- 遥操作组：可配置不同的遥操作组，灵活组合设备
- 实时状态监控：实时显示设备连接状态和运行情况
- 数据采集：支持遥操作过程中的数据采集和存储

## 技术架构

### 核心组件

#### BaseDevice 基类
所有设备的抽象基类，提供统一的接口：
- 事件回调机制
- 配置管理
- 连接状态管理

#### 设备类
- **Robot类**：机械臂控制抽象基类，具体实现如RM_controller
- **VRSocket类**：负责与VR头显的TCP连接和数据接收
- **Camera类**：摄像头设备抽象类，具体实现如RealSenseCamera

#### 核心业务逻辑
- **TeleopMiddleware**：处理VR数据并转换为机械臂控制指令
- **DataCollect**：数据采集模块，用于收集遥操作过程中的视频和状态数据
- **TeleopGroup**：遥操作组管理，协调多个设备协同工作

## 安装指南

### 环境要求
- Python 3.10+
- Windows/Linux/macOS

### 安装依赖
```bash
pip install -r requirements.txt
```

或者使用pyproject.toml:
```bash
pip install .
```

### 主要依赖
- FastAPI: Web框架
- OpenCV: 图像处理
- Pyrealsense2: RealSense摄像头支持
- PyORBBECSDK: ORBBEC摄像头支持
- robotic-arm: 机械臂控制库
- numpy, scipy: 科学计算

## 使用方法

### 启动服务
```bash
python run.py
```

访问 http://localhost:8000 查看Web界面

### Web界面功能
1. **设备管理**：
   - 查看所有设备状态
   - 添加/删除设备
   - 配置设备参数
   - 启动/停止设备

2. **遥操作组管理**：
   - 创建遥操作组
   - 配置组内设备（左右机械臂、VR头显、摄像头）
   - 启动/停止遥操作

### API接口
系统提供RESTful API接口，可通过 `/api` 路径访问各种功能。

## 项目结构
```
.
├── Device/                 # 设备相关模块
│   ├── Camera/             # 摄像头设备
│   ├── Robot/              # 机械臂设备
│   └── VR/                 # VR设备
├── static/                 # Web前端静态文件
├── test/                   # 测试文件
├── DataCollect.py          # 数据采集模块
├── TeleopGroup.py          # 遥操作组管理
├── TeleopMiddleware.py     # 遥操作中间件
├── server.py               # Web服务
└── run.py                  # 主程序入口
```

## 开发指南

### 添加新设备类型
1. 继承BaseDevice基类
2. 实现必要的接口方法（start, stop等）
3. 在Web界面中注册设备类型

### 扩展遥操作功能
1. 在TeleopMiddleware中添加新的事件处理
2. 在前端界面中添加相应的控制元素

## 注意事项

1. 所有设备的主循环都需要放在多线程中运行
2. 主线程需要运行Web服务，设备控制逻辑不能阻塞主线程
3. 设备状态有三种：未连接(0)、已连接(1)、断开连接(2)
4. 系统支持自动重连机制