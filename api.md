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

---

## 说明
- 所有设备均以卡片形式展示，支持动态添加、配置、启动、停止。
- 推荐使用 application/json。
- 设备配置字段请参考各设备类型说明。
- 启动/停止操作需设备已配置。
- 设备状态和日志可通过前端页面实时查看。

© 2025 SZUEAILab