# EasyTeleop 遥操作管理平台 API 文档（REST风格）

# 数据相关API

## 设备分类与列表

### GET /api/device/categories
- 描述：获取所有设备分类。
- 返回：
```json
{
  "categories": ["vr", "robot", "camera"]
}
```

### GET /api/device/types
- 描述：获取设备类型及对应配置字段。
- 查询参数：
  - category: "vr" | "robot" | "camera"
- 返回：
```json
{
  "RealMan": ["ip", "port"],
  "Quest": ["ip", "port"],
  "RealSense": ["camera_type", "camera_position", "camera_serial"]
}
```

### GET /api/devices
- 描述：获取所有设备列表。
- 查询参数（可选）：
  - category: "vr" | "robot" | "camera"
- 返回：
```json
[
  { "id": 1, "name": "Quest设备", "describe": "Quest VR设备","category":"vr", "type": "Quest", "config": {...} },
  { "id": 2, "name": "RealMan机械臂", "describe": "RealMan机器人","category":"robot", "type": "RealMan", "config": {...} },
  { "id": 3, "name": "RealSense相机", "describe": "RealSense深度相机","category":"camera", "type": "RealSense", "config": {...} }
]
```

---

## 设备添加与配置

### GET /api/devices/{id}
- 描述：获取单个设备详情。
- 路径参数：
  - id: 设备ID
- 返回：
```json
{ 
  "id": 3, 
  "name": "RealSense相机", 
  "describe": "RealSense深度相机", 
  "category": "camera",
  "type": "RealSense", 
  "config": {...} 
}
```

### POST /api/devices
- 描述：新增设备。
- 请求体（JSON）：
```json
{
  "name": "设备名称",
  "describe": "设备描述",
  "category": "vr" | "robot" | "camera",
  "type": "RealSense",
  "config": {
    "camera_type": "RealSense",
    "camera_position": "left_wrist",
    "camera_serial": "427622270438"
  }
}
```
- 返回（状态码：201 Created）：
```json
{ "message": "设备已添加" }
```

### PUT /api/devices/{id}
- 描述：修改设备配置。
- 路径参数：
  - id: 设备ID
- 请求体（JSON）：
```json
{
  "name": "设备名称",
  "describe": "设备描述",
  "category": "vr" | "robot" | "camera",
  "type": "RealSense",
  "config": {
    "camera_type": "RealSense",
    "camera_position": "left_wrist",
    "camera_serial": "427622270438"
  }
}
```
- 返回：
```json
{ "message": "配置已更新" }
```

### DELETE /api/devices/{id}
- 描述：彻底删除设备（从数据库移除）。
- 路径参数：
  - id: 设备ID
- 返回（状态码：204 No Content）：
```json
无返回内容
```

---

## 遥操作组管理

### GET /api/teleop-groups
- 描述：获取所有遥操作组列表。
- 返回：
```json
[
  { 
    "id": "group1", 
    "name": "主操作组",
    "describe": "主操作组描述",
    "left_arm_id": 1,
    "right_arm_id": 2,
    "vr_id": 3,
    "camera1_id": 4,
    "camera2_id": 5,
    "camera3_id": 6,
    "running": true 
  }
]
```

### POST /api/teleop-groups
- 描述：创建遥操作组。
- 请求体（JSON）：
```json
{ 
  "id": "group1",
  "name": "主操作组",
  "describe": "主操作组描述",
  "left_arm_id": 1,
  "right_arm_id": 2,
  "vr_id": 3,
  "camera1_id": 4,
  "camera2_id": 5,
  "camera3_id": 6
}
```
- 返回（状态码：201 Created）：
```json
{ "message": "遥操作组已创建" }
```

### PUT /api/teleop-groups/{group_id}
- 描述：更新遥操作组配置。
- 路径参数：
  - group_id: 组ID
- 请求体（JSON）：
```json
{ 
  "name": "主操作组",
  "describe": "主操作组描述",
  "left_arm_id": 1,
  "right_arm_id": 2,
  "vr_id": 3,
  "camera1_id": 4,
  "camera2_id": 5,
  "camera3_id": 6
}
```
- 返回：
```json
{ "message": "遥操作组已更新" }
```

### DELETE /api/teleop-groups/{group_id}
- 描述：删除遥操作组。
- 路径参数：
  - group_id: 组ID
- 返回（状态码：204 No Content）：
```json
无返回内容
```

### GET /api/teleop-groups/{group_id}
- 描述：获取遥操作组配置详情。
- 路径参数：
  - group_id: 组ID
- 返回：
```json
{ 
  "id": "group1",
  "name": "主操作组",
  "describe": "主操作组描述",
  "left_arm_id": 1,
  "right_arm_id": 2,
  "vr_id": 3,
  "camera1_id": 4,
  "camera2_id": 5,
  "camera3_id": 6,
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00",
  "is_active": true
}
```

# 控制逻辑相关

## 设备启动与停止

<p style = "color:red">注意下方设备的启动和停止接口考虑删除，请尽量不要使用</p>

### ~~POST /api/devices/{id}/start~~

- 描述：启动设备。
- 路径参数：
  - id: 设备ID
- 返回：
```json
{ "message": "设备已启动" }
```

### ~~POST /api/devices/{id}/stop~~
- 描述：停止设备。
- 路径参数：
  - id: 设备ID
- 返回：
```json
{ "message": "设备已停止并删除" }
```

### GET /api/devices/{id}/status
- 描述：获取设备连接状态（前端可轮询）。
- 路径参数：
  - id: 设备ID
- 返回：
```json
{ "conn_status": 0 }
```
- 状态码说明：
  - 0: 未连接
  - 1: 已连接
  - 2: 断开/异常

### POST /api/teleop-groups/{group_id}/start
- 描述：启动遥操作组。
- 路径参数：
  - group_id: 组ID
- 返回：
```json
{ "message": "遥操作已启动" }
```

### POST /api/teleop-groups/{group_id}/stop
- 描述：停止遥操作组。
- 路径参数：
  - group_id: 组ID
- 返回：
```json
{ "message": "遥操作已停止" }
```

### GET /api/teleop-groups/{group_id}/status
- 描述：获取遥操作组运行状态和数据采集状态。
- 路径参数：
  - group_id: 组ID
- 返回：
```json
{
  "running": true,
  "capture_state": 1
}
```
- 字段说明：
  - running: 遥操作组运行状态
    - true: 运行中
    - false: 已停止
  - capture_state: 数据采集状态
    - 0: 未采集
    - 1: 采集中

---

# 说明
- 所有设备均以卡片形式展示，支持动态添加、配置、启动、停止。
- 推荐使用 application/json。
- 设备配置字段请参考各设备类型说明。
- 启动/停止操作需设备已配置。
- 设备状态和日志可通过前端页面实时查看。

© 2025 SZUEAILab