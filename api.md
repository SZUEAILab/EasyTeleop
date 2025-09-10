
# EasyTeleop 遥操作管理平台 API 文档（卡片式设备管理）

## 设备列表与详情

### GET /devices
- 描述：获取所有设备列表（按类别分组）。
- 返回：
```json
{
  "vr": [{ "id": 1, "type": "Quest", "config": {...} }],
  "arm": [{ "id": 2, "type": "RealMan", "config": {...} }],
  "camera": [{ "id": 3, "type": "RealSense", "config": {...} }]
}
```

### GET /device/{category}/{id}
- 描述：获取单个设备详情。
- 路径参数：
  - category: "vr" | "arm" | "camera"
  - id: 设备ID
- 返回：
```json
{ "id": 3, "type": "RealSense", "config": {...} }
```

### GET /device/{category}/adapted_types
- 描述：获取设备类型及对应配置字段。
- 路径参数：
  - category: "vr" | "arm" | "camera"
- 返回：
```json
{
  "RealMan": ["ip", "port"],
  "TestArm": ["ip", "port", "model"]
}
```

---

## 设备添加与配置

### POST /device/{category}/add
- 描述：新增设备（添加卡片）。
- 路径参数：
  - category: "vr" | "arm" | "camera"
- 请求体（JSON）：
```json
{ "type": "RealSense", "config": { "camera_type": "RealSense", "camera_position": "left_wrist", "camera_serial": "427622270438" } }
```
- 返回：
```json
{ "msg": "设备已添加" }
```

### PUT /device/{category}/{id}/config
- 描述：修改设备配置（卡片内配置按钮）。
- 路径参数：
  - category: "vr" | "arm" | "camera"
  - id: 设备ID
- 请求体（JSON）：
```json
{ "config": { ... } }
```
- 返回：
```json
{ "msg": "配置已更新" }
```

---

## 设备启动与停止

### POST /device/{category}/{id}/start
- 描述：启动设备（卡片内开始按钮）。
- 路径参数：
  - category: "vr" | "arm" | "camera"
  - id: 设备ID
- 返回：
```json
{ "msg": "设备已启动" }
```

### POST /device/{category}/{id}/stop
- 描述：停止设备（卡片内结束按钮）。
- 路径参数：
  - category: "vr" | "arm" | "camera"
  - id: 设备ID
- 返回：
```json
{ "msg": "设备已停止并删除" }
```

### DELETE /device/{category}/{id}/delete
- 描述：彻底删除设备（从数据库移除）。
- 路径参数：
  - category: "vr" | "arm" | "camera"
  - id: 设备ID
- 返回：
```json
{ "msg": "设备已彻底删除" }
```

### GET /device/{category}/{id}/conn_status
- 描述：获取设备连接状态（前端可轮询）。
- 路径参数：
  - category: "vr" | "arm" | "camera"
  - id: 设备ID
- 返回：
```json
{ "conn_status": 0 }
```
- 状态码说明：
  - 0: 未连接
  - 1: 已连接
  - 2: 断开/异常

---

## 遥操作组管理

### GET /teleop/list
- 描述：获取所有遥操作组列表。
- 返回：
```json
[{ "id": "group1", "config": {...}, "running": true }]
```

### POST /teleop/{group_id}
- 描述：创建遥操作组。
- 路径参数：
  - group_id: 组ID
- 请求体（JSON）：
```json
{ "left_arm": 1, "right_arm": 2, "vr": 3 }
```
- 返回：
```json
{ "msg": "遥操作组已创建" }
```

### PUT /teleop/{group_id}
- 描述：更新遥操作组配置。
- 路径参数：
  - group_id: 组ID
- 请求体（JSON）：
```json
{ ... }
```
- 返回：
```json
{ "msg": "遥操作组已更新" }
```

### DELETE /teleop/{group_id}
- 描述：删除遥操作组。
- 路径参数：
  - group_id: 组ID
- 返回：
```json
{ "msg": "遥操作组已删除" }
```

### GET /teleop/{group_id}
- 描述：获取遥操作组详情。
- 路径参数：
  - group_id: 组ID
- 返回：
```json
{ "id": "group1", "config": {...}, "running": true }
```

### POST /teleop/{group_id}/start
- 描述：启动遥操作组。
- 路径参数：
  - group_id: 组ID
- 返回：
```json
{ "msg": "遥操作已启动" }
```

### POST /teleop/{group_id}/stop
- 描述：停止遥操作组。
- 路径参数：
  - group_id: 组ID
- 返回：
```json
{ "msg": "遥操作已停止" }
```

---

## 说明
- 所有设备均以卡片形式展示，支持动态添加、配置、启动、停止。
- 推荐使用 application/json。
- 设备配置字段请参考各设备类型说明。
- 启动/停止操作需设备已配置。
- 设备状态和日志可通过前端页面实时查看。

© 2025 SZUEAILab