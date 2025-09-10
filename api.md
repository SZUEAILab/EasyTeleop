# EasyTeleop 遥操作管理平台 API 文档

## 设备配置

### POST /config
- 描述：保存设备组配置（VR头显、机械臂、摄像头）。
- 请求体（JSON）：
```json
{
	"vr_ip": "192.168.1.100",
	"vr_port": 9000,
	"arms": [
		{"ip": "192.168.1.101", "port": 8001},
		{"ip": "192.168.1.102", "port": 8002}
	],
	"cameras": [
		{"type": "RealSense", "position": "front", "serial": "123456"}
	]
}
```
- 返回：
```json
{"msg": "配置已保存"}
```

### GET /config
- 描述：获取当前设备组配置。
- 返回：
```json
{
	"vr_ip": "192.168.1.100",
	"vr_port": 9000,
	"arms": [...],
	"cameras": [...]
}
```

---

## 设备连接

### POST /connect/vr
- 描述：连接 VR 头显。
- 返回：
```json
{"msg": "VR已连接"}
```

### POST /connect/arm
- 描述：连接所有配置的机械臂。
- 返回：
```json
{"msg": "机械臂已连接"}
```

### POST /connect/camera
- 描述：连接所有配置的摄像头。
- 返回：
```json
{"msg": "摄像头已连接"}
```

---

## 设备查询

### GET /devices/{type}
- 描述：查询指定类型设备池状态。
- 路径参数：
	- type: "vr" | "arm" | "camera"
- 返回：
```json
{"devices": ["main", "arm_0", "arm_1", "manager"]}
```

---

## 遥操作启动

### POST /start_teleop
- 描述：启动遥操作流程，注册 VR 消息回调。
- 返回：
```json
{"msg": "遥操作已启动"}
```

---

## 其他说明
- 所有接口均为 RESTful 风格，推荐使用 application/json。
- 设备组配置需至少包含一个机械臂（默认左臂），最多两个机械臂，唯一头显，摄像头可多个。
- 启动遥操作前需保证设备已连接。
- 设备状态和日志可通过前端页面实时查看。

---

© 2025 SZUEAILab