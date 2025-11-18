# 数据采集与存储格式规范

## 1. Temp文件夹下的临时数据存储格式

### 1.1 目录结构
```
datasets/temp/
├── session_timestamp1/
│   ├── metadata.json
│   ├── frames/
│   │   ├── camera_0/
│   │   │   ├── frame_1634567890.123.jpg
│   │   │   ├── frame_1634567890.456.jpg
│   │   │   └── ...
│   │   ├── camera_1/
│   │   │   ├── frame_1634567890.123.jpg
│   │   │   ├── frame_1634567890.456.jpg
│   │   │   └── ...
│   │   └── camera_2/
│   │       ├── frame_1634567890.123.jpg
│   │       ├── frame_1634567890.456.jpg
│   │       └── ...
│   ├── poses.csv
│   └── joints.csv
├── session_timestamp2/
│   └── ...
```

### 1.2 文件详细说明

#### metadata.json
包含本次会话的元数据信息：
```json
{
  "session_id": "session_timestamp",
  "start_time": 1634567890.123,
  "end_time": 1634568890.456,
  "devices": {
    "cameras": {
      "camera_0": {
        "type": "RealSenseCamera",
        "serial": "153122070447",
        "fps": 30
      },
      "camera_1": {
        "type": "RealSenseCamera",
        "serial": "123456789012",
        "fps": 30
      },
      "camera_2": {
        "type": "RealSenseCamera",
        "serial": "098765432109",
        "fps": 30
      }
    },
    "robot": {
      "type": "RealMan",
      "joints": 6
    }
  }
}
```

#### 视频帧文件 (frames/)
- 每个摄像头有独立的目录，命名为`camera_{id}`，其中id为摄像头编号（从0开始）
- 文件命名格式: `frame_{timestamp}.jpg`
- 时间戳精确到毫秒级别
- 每个文件为单独的JPEG图像

#### 位姿状态文件 (poses.csv)
- 所有位姿状态都存储在这个CSV文件中
- 每一行代表一个位姿数据点
- CSV格式:
  ```
  timestamp,index,value
  1634567890.100,0,0.123
  1634567890.100,1,0.456
  1634567890.100,2,0.789
  ...
  ```

其中：
- `timestamp`: 数据点的时间戳
- `index`: 位姿数据索引（0-5通常表示x, y, z, rx, ry, rz）
- `value`: 对应索引的位姿值

#### 关节状态文件 (joints.csv)
- 所有关节状态都存储在这个CSV文件中
- 每一行代表一个关节数据点
- CSV格式:
  ```
  timestamp,index,value
  1634567890.100,0,1.23
  1634567890.100,1,0.45
  1634567890.100,2,2.34
  ...
  ```

其中：
- `timestamp`: 数据点的时间戳
- `index`: 关节索引
- `value`: 对应索引的关节值

## 2. HDF5后处理格式 (用于pi0, act, rdt使用)

### 2.1 文件结构
```
dataset.hdf5
├── episodes/
│   ├── episode_0/
│   │   ├── observations/
│   │   │   ├── images/
│   │   │   │   ├── camera_0/
│   │   │   │   │   ├── 0.jpg
│   │   │   │   │   ├── 1.jpg
│   │   │   │   │   └── ...
│   │   │   │   ├── camera_1/
│   │   │   │   │   ├── 0.jpg
│   │   │   │   │   ├── 1.jpg
│   │   │   │   │   └── ...
│   │   │   │   └── camera_2/
│   │   │   │       ├── 0.jpg
│   │   │   │       ├── 1.jpg
│   │   │   │       └── ...
│   │   │   └── state/
│   │   │       ├── pose
│   │   │       └── joint
│   │   ├── actions/
│   │   │   ├── pose
│   │   │   ├── joint
│   │   │   └── timestamps
│   │   └── rewards/
│   │       └── values
│   └── episode_1/
│       └── ...
├── metadata/
│   ├── cameras/
│   ├── robots/
│   └── timestamps/
└── info/
    ├── total_episodes
    ├── total_frames
    ├── num_cameras
    └── version
```

### 2.2 数据对齐与插值处理

在后处理阶段，需要将不同采样率的视频帧和关节状态进行时间对齐：

1. 对于每个episode：
   - 获取所有视频帧的时间戳序列 T_img（合并所有摄像头的时间戳并去重）
   - 获取所有位姿状态的时间戳序列 T_pose
   - 获取所有关节状态的时间戳序列 T_joint
   - 对每个图像时间戳 t_img ∈ T_img：
     - 找到最近的位姿状态时间戳 t_pose1, t_pose2，使得 t_pose1 ≤ t_img ≤ t_pose2
     - 找到最近的关节状态时间戳 t_joint1, t_joint2，使得 t_joint1 ≤ t_img ≤ t_joint2
     - 使用线性插值得到 t_img 时刻的位姿和关节状态

### 2.3 HDF5数据集详细描述

| 数据集路径 | 数据类型 | 形状 | 描述 |
|-----------|---------|------|------|
| `/episodes/episode_{i}/observations/images/cam_wrist` | bytes | (N,) | 第0个摄像头的JPEG图像数据数组 |
| `/episodes/episode_{i}/observations/images/cam_{id}` | bytes | (N,) | 第id个摄像头的JPEG图像数据数组 |
| `/episodes/episode_{i}/observations/state/pose` | float32 | (N, P) | 位姿状态 |
| `/episodes/episode_{i}/observations/state/joint` | float32 | (N, J) | 关节状态 |
| `/episodes/episode_{i}/actions/pose` | float32 | (N, P) | 动作位姿 |
| `/episodes/episode_{i}/actions/joint` | float32 | (N, J) | 动作关节值 |
| `/episodes/episode_{i}/actions/timestamps` | float64 | (N,) | 动作时间戳 |
| `/metadata/cameras` | string | (C,) | 相机信息 |
| `/metadata/robots` | string | (R,) | 机器人信息 |
| `/info/total_episodes` | int | (1,) | 总片段数 |
| `/info/num_cameras` | int | (1,) | 摄像头数量 |

其中：
- N: 序列长度
- P: 位姿维度（通常是6维：x, y, z, rx, ry, rz）
- J: 关节数量
- C: 摄像头数量
- R: 机器人数量

### 2.4 图像数据格式说明

图像数据存储为JPEG格式的字节数组，每个摄像头的数据存储为一个一维数组，数组中的每个元素都是一个JPEG图像的字节数据。这种格式与view_hdf5工具兼容，可以直接被读取和显示。

## 3. 时间戳同步策略

### 3.1 数据收集阶段
- 所有设备数据都需要附带高精度时间戳（Unix时间戳，浮点数，单位秒）
- 每个摄像头的视频帧保存在独立的目录中，机器人位姿和关节数据分别保存在独立的CSV文件中

### 3.2 后处理阶段
1. 加载一个session的所有数据
2. 对所有摄像头的图像时间戳进行合并和排序
3. 从poses.csv和joints.csv中分别加载位姿和关节数据
4. 对每个图像时间戳，分别查找相邻的位姿和关节时间戳
5. 使用线性插值分别得到图像时间戳对应的位姿和关节状态
6. 构建HDF5文件，将对齐后的数据存储进去

这种设计能够确保：
- 原始数据完整性得以保留
- 支持多摄像头数据采集和存储
- 位姿和关节数据分离存储，提高处理效率
- 减少文件系统开销，提高处理效率
- 时间同步准确
- 支持后续灵活的数据处理和分析
- 兼容pi0, act, rdt等系统的数据格式要求