# Easy Teleoperate Tools

EasyTeleop 是一个基于VR设备控制机械臂的遥操作工具集。该工具集支持多种设备的集成，包括RealMan机械臂、VR头显和RealSense摄像头，并提供接口进行设备管理和遥操作控制。

> 本项目已发布到PYPI，可以使用 pip 安装：`pip install easyteleop`

## 功能特性

- 多设备管理：支持机械臂、VR头显和摄像头设备的统一管理
- 遥操作组：可配置不同的遥操作组，灵活组合设备
- 实时状态监控：实时显示设备连接状态和运行情况
- 数据采集：支持遥操作过程中的数据采集和存储
- WebRTC视频流传输：支持低延迟视频流传输
- 可视化：提供姿态可视化功能
- qpSWIFT优化：集成qpSWIFT二次规划求解器，用于机器人逆运动学求解

## 系统架构

本系统采用模块化架构，包含以下几个主要组件：

### 组件 (Components)
- DataCollect: 数据采集模块
- TeleopMiddleware: 遥操作中间件
- Visualizer: 可视化模块
- WebRTC: WebRTC视频流支持
- VRPacketAnalyzer: VR数据包分析器
- Interpolation: 插值算法
- HandVisualizer: 手部可视化模块

### 设备模块 (Device)
详细使用参考[设备模块文档](/docs/device.md)
- BaseDevice: 设备基类
- Camera: 摄像头设备（RealSenseCamera, TestCamera等）
- Robot: 机械臂设备（RealMan, TestRobot等）
- Hand: 手部设备（Revo2OnRealMan等）
- VR: VR设备（VRSocket, TestVR等）

### 遥操作组 (TeleopGroup)
详细使用参考[遥操组模块文档](/docs/teleop_group.md)
- BaseTeleopGroup: 遥操作组基类
- SingleArmWithTriggerTeleopGroup: 单臂触发遥操作组
- TwoArmWithTriggerTeleopGroup: 双臂触发遥操作组

## 安装指南

### 环境要求
- Python 3.10+
- Windows/Linux/macOS
- uv 包管理器

### 安装依赖

使用uv管理项目依赖：(不能uv sync因为编辑式安装不能编译C拓展)
```bash
# 安装uv（如果尚未安装）
pip install uv

# 安装项目依赖
uv pip install -e .

```

### 主要依赖
- aiortc: WebRTC支持
- opencv-python: 图像处理
- pyrealsense2: RealSense摄像头支持
- robotic-arm: 机械臂控制库
- numpy, scipy: 科学计算
- matplotlib: 数据可视化
- qpSWIFT: 二次规划求解器（已集成到包中）

## 安装与依赖（新版）

### 环境要求
- Python 3.10+
- Windows/Linux/macOS（建议官方 Python 或 Conda）
- 可选：uv 包管理器（更快的 pip 替代品）

### 正式安装（推荐）
- 从 PyPI 安装（wheel 已内置 qpSWIFT 扩展，开箱即用）
```bash
pip install easyteleop
```

### 开发者安装（本地源码 + 编译内置 qpSWIFT）
- 需要本地 C/C++ 构建环境：
  - Windows：Visual Studio Build Tools（含“使用 C++ 的桌面开发”组件）
  - Linux：gcc/clang 与基础构建工具
  - macOS：Xcode Command Line Tools
- 注意：仅执行 `uv sync` 只会安装第三方依赖，不会安装（编译）本包本身；必须安装本包才会编译 qpSWIFT 扩展。

使用 uv（推荐）：
```bash
pip install uv  # 如未安装
uv pip install -e .
```

或使用 pip：
```bash
pip install -e .
```

安装完成后验证：
```bash
python -c "import EasyTeleop, qpSWIFT; print('OK')"
```

### 从源码构建 Wheel（用于分发）
```bash
uv build            # 生成 sdist 与 wheel
# 或仅生成 wheel：
uv build --wheel
```
构建好的 wheel 中已内置编译完成的 `qpSWIFT` 扩展（与当前平台/解释器匹配）。

### 主要依赖（摘要）
- aiortc, opencv-python, pyrealsense2, robotic-arm, numpy, scipy, matplotlib
- qpSWIFT（二次规划求解器，已随包集成并在安装时编译/或随 wheel 分发）

## 使用方法

### 简单遥操

在[run](file:///e:/Project/EasyTeleop/run)文件夹下放有一些测试文件，用于直接启动遥操

- run_test.py:双臂和摄像头都采用Test类，VR头显采用VRSocket类

### 启动服务

运行测试脚本:
```bash
# 在项目根目录下
uv run run/run_test.py
```

## 项目结构
```
.
├── run/                    # 运行脚本
│   ├── run_test.py         # 测试脚本示例
│   └── ...                 # 其他运行脚本
├── src/
│   └── EasyTeleop/
│       ├── Components/     # 核心组件模块
│       │   ├── DataCollect.py      # 数据采集模块
│       │   ├── TeleopMiddleware.py # 遥操作中间件
│       │   ├── WebRTC.py           # WebRTC支持
│       │   ├── VRPacketAnalyzer.py # VR数据包分析器
│       │   ├── Interpolation.py    # 插值算法
│       │   ├── Visualizer.py       # 可视化模块
│       │   ├── HandVisualizer.py   # 手部可视化模块
│       │   └── __init__.py
│       ├── Device/         # 设备相关模块
│       │   ├── BaseDevice.py       # 设备基类
│       │   ├── Camera/             # 摄像头设备
│       │   │   ├── BaseCamera.py
│       │   │   ├── RealSenseCamera.py
│       │   │   ├── TestCamera.py
│       │   │   └── __init__.py
│       │   ├── Robot/              # 机械臂设备
│       │   │   ├── BaseRobot.py
│       │   │   ├── RealMan.py
│       │   │   ├── TestRobot.py
│       │   │   └── __init__.py
│       │   ├── Hand/               # 手部设备
│       │   │   ├── BaseHand.py
│       │   │   ├── Revo2OnRealMan.py
│       │   │   └── __init__.py
│       │   ├── VR/                 # VR设备
│       │   │   ├── BaseVR.py
│       │   │   ├── TestVR.py
│       │   │   ├── VRSocket.py
│       │   │   └── __init__.py
│       │   └── __init__.py
│       ├── TeleopGroup/    # 遥操作组管理
│       │   ├── BaseTeleopGroup.py
│       │   ├── SingleArmWithTriggerTeleopGroup.py
│       │   ├── TwoArmWithTriggerTeleopGroup.py
│       │   └── __init__.py
│       └── __init__.py
├── test/                   # 测试文件
├── docs/                   # 文档
└── pyproject.toml          # 项目配置文件
```

## 开发指南

### 添加新设备类型
1. 继承BaseDevice基类（或相应设备类型的基类）
2. 实现必要的接口方法（start, stop等）
3. 在TeleopMiddleware中注册相应的事件处理函数

### 扩展遥操作功能
1. 在TeleopMiddleware中添加新的事件处理
2. 创建新的遥操作组来组织设备

## 构建和发布

使用uv构建分发包：
```bash
uv build
```

配置好API密钥然后上传PYPI
```bash
uv publish
```

或者使用传统方法构建并发布
```bash
python -m build
python -m twine upload dist/*
```

## 注意事项

1. 所有设备的主循环都需要放在多线程中运行
2. 设备控制逻辑不能阻塞主线程
3. 设备状态有三种：未连接(0)、已连接(1)、断开连接(2)
4. 系统支持自动重连机制
