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
- Windows/Linux/macOS（建议官方 Python 或 Conda）
- 可选：uv 包管理器（更快的 pip 替代品）

### 克隆仓库（包含子模块）

由于项目使用了 Git 子模块（qp-tools），需要特殊处理来完整克隆仓库：

```bash
# 方法1：克隆时初始化子模块
git clone --recurse-submodules https://github.com/Chain-Pray/EasyTeleop.git

# 方法2：克隆后手动初始化和更新子模块
git clone https://github.com/Chain-Pray/EasyTeleop.git
cd EasyTeleop
git submodule init
git submodule update
```

### 安装方式

#### 正式安装（推荐）
从 PyPI 安装（wheel 已内置 qpSWIFT 扩展，开箱即用）
```bash
pip install easyteleop
```

#### 开发者安装（本地源码 + 编译内置 qpSWIFT）
需要本地 C/C++ 构建环境：
  - Windows：Visual Studio Build Tools（含"使用 C++ 的桌面开发"组件）
  - Linux：gcc/clang 与基础构建工具
  - macOS：Xcode Command Line Tools

使用 uv（推荐）：
```bash
pip install uv  # 如未安装
uv pip install -e .
```

或使用 pip：
```bash
pip install -e .
```

注意：仅执行 `uv sync` 只会安装第三方依赖，不会安装（编译）本包本身；必须安装本包才会编译 qpSWIFT 扩展。

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

### 主要依赖
- aiortc: WebRTC支持
- opencv-python: 图像处理
- pyrealsense2: RealSense摄像头支持
- robotic-arm: 机械臂控制库
- numpy, scipy: 科学计算
- matplotlib: 数据可视化
- qpSWIFT: 二次规划求解器（已随包集成并在安装时编译/或随 wheel 分发）

## 使用方法

### 简单遥操

在[run](/run)文件夹下提供了多种测试脚本，用于不同场景的遥操作：

- [run_test.py](run/run_test.py): 双臂和摄像头都采用Test类，VR头显采用VRSocket类，适合功能测试
- [run_two_arm.py](run/run_two_arm.py): 使用真实的RealMan机械臂，适合实际操作
- [run_webrtc.py](run/run_webrtc.py): 支持WebRTC视频流传输，可与Unity客户端配合使用
- [run_pose_visualize.py](run/run_pose_visualize.py): 姿态可视化演示
- [run_hand_visualize.py](run/run_hand_visualize.py): 手部可视化演示
- [run_singel_arm_with_right_controller.py](run/run_singel_arm_with_right_controller.py): 单臂控制示例
- [run_interpolation.py](run/run_interpolation.py): 插值算法演示

### 启动服务

运行测试脚本:
```bash
# 在项目根目录下
uv run run/run_test.py
```

### 自定义遥操作脚本

创建自己的遥操作脚本通常包括以下步骤：

1. 导入所需的设备和组件：
```python
from EasyTeleop.Components import TeleopMiddleware
from EasyTeleop.Device.VR import VRSocket
from EasyTeleop.Device.Robot import RealMan
```

2. 初始化设备实例：
```python
# 初始化VR设备
vrsocket = VRSocket({"ip": '192.168.0.127', "port": 12345})

# 初始化机械臂设备
l_arm = RealMan({"ip": "192.168.0.18", "port": 8080})
r_arm = RealMan({"ip": "192.168.0.19", "port": 8080})
```

3. 创建中间件并注册事件回调：
```python
teleop = TeleopMiddleware()

# 注册VR事件回调
teleop.on("leftGripTurnDown", l_arm.start_control)
teleop.on("leftGripTurnUp", l_arm.stop_control)
teleop.on("leftPosRot", l_arm.add_pose_data)

# 注册VR数据处理回调
vrsocket.on("message", teleop.handle_socket_data)
```

4. 启动所有设备和服务：
```python
l_arm.start()
r_arm.start()
vrsocket.start()
```

5. 添加主循环以监控设备状态：
```python
devices = [l_arm, r_arm, vrsocket]
while True:
    connect_states = [device.get_conn_status() for device in devices]
    print(f"设备连接状态: {connect_states}")
    time.sleep(1)
```

### WebRTC视频流传输

要使用WebRTC功能，需要：

1. 初始化摄像头设备：
```python
from EasyTeleop.Device.Camera import RealSenseCamera
camera = RealSenseCamera({"serial": "相机序列号", "target_fps": 30})
```

2. 创建流跟踪器和WebRTC客户端：
```python
from EasyTeleop.Components.WebRTC import CameraDeviceStreamTrack, UnityWebRTC
tracker = CameraDeviceStreamTrack()
client = UnityWebRTC(connection_id="LeftEye", signaling_url="你的信令服务器地址", tracker=tracker)
```

3. 注册帧回调函数：
```python
def frame_callback(frame):
    tracker.put_frame(frame)

camera.on("frame", frame_callback)
```

4. 启动异步连接：
```python
async def main():
    await client.connect()

asyncio.run(main())
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

要添加一个新的设备类型，需要遵循以下步骤：

1. 在相应的设备类别目录下创建新设备类（如在[Device/Robot](src/EasyTeleop/Device/Robot)中创建新类）：
```python
from EasyTeleop.Device.BaseDevice import BaseDevice

class MyNewRobot(BaseDevice):
    name = "My New Robot"
    description = "A new robot device for teleoperation"
    need_config = {
        "ip": "str",
        "port": "int"
    }
    
    def set_config(self, config):
        # 验证并设置配置
        super().set_config(config)
        self.ip = config.get("ip")
        self.port = config.get("port")
        return True

    def _connect_device(self):
        # 实现设备连接逻辑
        # 返回True表示连接成功
        return True

    def _disconnect_device(self):
        # 实现设备断开连接逻辑
        # 返回True表示断开成功
        return True

    def _main(self):
        # 实现设备主循环逻辑
        # 这个方法会在独立线程中循环调用
        pass
```

2. 确保新设备类继承自相应的基类（如[BaseDevice](src/EasyTeleop/Device/BaseDevice.py)或特定设备类型的基类）

3. 实现必要的接口方法：
   - [set_config](src/EasyTeleop/Device/BaseDevice.py#L239-L249): 设置和验证设备配置
   - [_connect_device](src/EasyTeleop/Device/BaseDevice.py#L218-L225): 连接设备的具体实现
   - [_disconnect_device](src/EasyTeleop/Device/BaseDevice.py#L227-L234): 断开设备连接的具体实现
   - [_main](src/EasyTeleop/Device/BaseDevice.py#L212-L216): 设备主逻辑，在独立线程中运行

4. 定义设备所需的配置字段（[need_config](src/EasyTeleop/Device/BaseDevice.py#L13-L15)静态字段）

5. 在设备类中可以使用事件系统与系统其他部分通信：
```python
# 触发事件
self.emit("status_change", {"status": "running"})

# 注册事件回调
@device.on("frame")
def handle_frame(frame):
    # 处理帧数据
    pass
```

### 扩展遥操作功能

要扩展遥操作功能，可以通过以下方式：

1. 在[TeleopMiddleware](src/EasyTeleop/Components/TeleopMiddleware.py)中添加新的事件处理：
```python
# 添加新的事件类型
self._events["newFeature"] = self._default_callback

# 或者直接注册回调函数
teleop.on("newFeature", callback_function)
```

2. 创建新的遥操作组来组织设备：
```python
from EasyTeleop.TeleopGroup.BaseTeleopGroup import BaseTeleopGroup

class MyTeleopGroup(BaseTeleopGroup):
    name = "My Teleop Group"
    description = "A custom teleoperation group"
    need_config = ["left_arm", "right_arm", "vr"]

    def start(self):
        # 实现启动逻辑
        self.running = True
        return True

    def stop(self):
        # 实现停止逻辑
        self.running = False
        return True
```

### 事件驱动架构

系统采用事件驱动架构，设备和组件之间通过事件进行通信：

1. 设备通过emit方法触发事件：
```python
self.emit("frame", frame_data)
```

2. 其他组件通过on方法注册事件回调：
```python
device.on("frame", callback_function)
```

3. 支持装饰器语法注册回调：
```python
@device.on("frame")
def process_frame(frame):
    # 处理帧数据
    pass
```

### 多线程和并发处理

所有设备都在独立线程中运行，确保不会阻塞主线程：

1. 设备的主循环在[_main_loop](src/EasyTeleop/Device/BaseDevice.py#L154-L173)方法中实现
2. [_main](src/EasyTeleop/Device/BaseDevice.py#L212-L216)方法在独立线程中循环调用
3. 事件回调在独立线程中执行，避免阻塞设备主循环

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

### GitHub Actions自动化构建与发布

本项目使用GitHub Actions实现自动化构建和发布流程，每当创建新的Release时会自动触发。

#### 构建流程

1. **多平台wheel构建**：使用[cibuildwheel](https://github.com/pypa/cibuildwheel)为以下平台构建wheel包：
   - Ubuntu (Linux)
   - Windows
   - (macOS暂时存在编译问题)

2. **源码分发包构建**：在Ubuntu环境下构建源码分发包(sdist)

3. **发布到PyPI**：使用Trusted Publishing将构建产物发布到PyPI

#### 工作流配置

工作流文件位于[.github/workflows/python-publish.yml](.github/workflows/python-publish.yml)，包含以下关键配置：

- 构建Python 3.10、3.11和3.12的wheel包
- 跳过32位架构和PyPy实现
- Linux平台仅构建x86_64架构
- 使用PyPI Trusted Publishing进行安全发布

#### 发布新版本

要发布新版本，请按以下步骤操作：

1. 更新[pyproject.toml](pyproject.toml)中的版本号：
   ```toml
   [project]
   version = "x.x.x"
   ```

2. 提交更改并推送：
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to x.x.x"
   git push
   ```

3. 在GitHub上创建并发布新的Release：
   - 转到[Releases](https://github.com/Chain-Pray/EasyTeleop/releases)
   - 点击"Draft a new release"
   - 创建新的tag（格式：vX.X.X）
   - 填写Release标题和说明
   - 点击"Publish release"

4. GitHub Actions将自动触发构建和发布流程，构建完成后包将自动上传到PyPI

## 注意事项

1. 所有设备的主循环都需要放在多线程中运行
2. 设备控制逻辑不能阻塞主线程
3. 设备状态有三种：未连接(0)、已连接(1)、断开连接(2)
4. 系统支持自动重连机制