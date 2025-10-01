# Easy Teleoperate System

RealMan Teleoperate System 是一个基于VR设备控制机械臂的遥操作系统。该系统支持多种设备的集成，包括RealMan机械臂、VR头显和RealSense摄像头，并提供Web界面进行设备管理和遥操作控制。

## 功能特性

- 多设备管理：支持机械臂、VR头显和摄像头设备的统一管理
- Web界面控制：提供直观的Web界面进行设备配置和状态监控
- 遥操作组：可配置不同的遥操作组，灵活组合设备
- 实时状态监控：实时显示设备连接状态和运行情况
- 数据采集：支持遥操作过程中的数据采集和存储

## 系统架构

本系统采用分布式架构，包含两个主要组件：

### Backend (后端服务)
- 使用Go语言开发
- 负责提供Web管理界面
- 管理多个Node节点的注册和通信
- 提供RESTful API接口

### Node (设备控制节点)
- 使用Python开发
- 负责直接控制硬件设备（机械臂、VR、摄像头等）
- 通过WebSocket与Backend通信
- 支持多实例部署，每个Node可管理一组设备

两者通过WebSocket RPC协议进行通信，实现设备控制与Web管理的分离。

## 安装指南

### 环境要求
- Python 3.10+
- Windows/Linux/macOS
- uv 包管理器

### 安装依赖

使用uv管理项目依赖：
```bash
# 安装uv（如果尚未安装）
pip install uv

# 安装项目依赖
uv sync
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

1. 启动Backend服务（python替代）:
```bash
# 在Backend项目目录下
uv run server.py
```

2. 启动Node节点（Python服务）:
```bash
uv run run.py
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
├── Components/             # 核心组件模块
│   ├── DataCollect.py      # 数据采集模块
│   ├── TeleopMiddleware.py # 遥操作中间件
│   └── WebSocketRPC.py     # WebSocket RPC通信
├── Device/                 # 设备相关模块
│   ├── Camera/             # 摄像头设备
│   ├── Robot/              # 机械臂设备
│   └── VR/                 # VR设备
├── TeleopGroup/            # 遥操作组管理
├── WebRTC/                 # WebRTC视频流支持
├── static/                 # Web前端静态文件
├── test/                   # 测试文件
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