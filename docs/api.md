# EasyTeleop API 文档

## 概述

本文档描述了 EasyTeleop 系统的 RESTful API 接口，包括节点注册、设备管理和遥操作组管理等功能。

EasyTeleop 采用分布式架构设计，由 Go 后端服务和 Python Node 控制节点组成：
- Go 后端服务负责配置管理、数据库维护和任务调度
- Python Node 负责设备控制和状态管理
- 两者通过 WebSocket 进行 JSON-RPC 通信

## 节点管理

### POST `/api/node`

**节点注册**

描述：节点上线后发送注册请求，后端返回注册的 node_id 

**请求体 (JSON)**

```json
{
    "uuid": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"
}
```

**返回 (状态码：201 Created)**

```json
{
    "id": 5,
}
```

### GET `/api/nodes`

**获取节点列表**

描述：获取所有已注册节点的信息

**查询参数：**
- uuid: 可选，根据节点UUID过滤结果

**返回：**

```json
[
  {
    "id": 1,
    "uuid": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed",
    "status": 1,
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00"
  },
  {
    "id": 2,
    "uuid": "2c8e7cde-ccfe-5c3e-ac6e-bc9egccf5cef",
    "status": 0,
    "created_at": "2025-01-02T00:00:00",
    "updated_at": "2025-01-02T00:00:00"
  }
]
```

## 设备管理

### GET `/api/device/categories`

**获取设备分类**

描述：获取所有设备分类。

**查询参数：**
- node_id: 必须，节点ID

**返回：**

```json
["Camera", "Robot", "VR"]
```

### GET `/api/device/types`

**获取设备类型信息**

描述：获取所有设备类型及对应 type_info 字典，包括 name、description 和 need_config 字段。

**查询参数：**
- node_id：必须，节点ID

**返回：**

```json
{
  "Camera": {
    "RealSenseCamera": {
      "name": "通用RealSense摄像头",
      "description": "有线连接的RealSense摄像头设备",
      "need_config": {
        "serial": {
          "type": "string",
          "description": "RealSense设备序列号"
        },
        "target_fps": {
          "type": "integer",
          "description": "目标帧率,0为不控制",
          "default": 30
        }
      }
    }
  },
  "Robot": {
    "RealMan": {
      "name": "睿尔曼R75机械臂",
      "description": "用于控制RealMan机械臂的机器人控制器",
      "need_config": {
        "ip": {
          "type": "string",
          "description": "服务器IP地址"
        },
        "port": {
          "type": "integer",
          "description": "服务器端口号",
          "default": 8080
        }
      }
    }
  },
  "VR": {
    "VRSocket": {
      "name": "TCP Socket 头显",
      "description": "使用TCP Socket连接的VR设备",
      "need_config": {
        "ip": {
          "type": "string",
          "description": "服务器IP地址"
        },
        "port": {
          "type": "integer",
          "description": "服务器端口号",
          "default": 12345
        }
      }
    }
  }
}
```

### GET `/api/devices`

**获取设备列表**

描述：获取所有设备列表。

**查询参数：**
- node_id: 可选，节点ID

**返回：**

```json
[
  { 
    "id": 1,
    "node_id": 1, 
    "name": "Quest设备", 
    "description": "Quest VR设备",
    "category": "VR", 
    "type": "Quest", 
    "config": {
      "ip": "192.168.1.100",
      "port": 12345
    },
    "status": 0,
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00"
  },
  { 
    "id": 2,
    "node_id": 1, 
    "name": "RealMan机械臂", 
    "description": "RealMan机器人",
    "category": "Robot", 
    "type": "RealMan", 
    "config": {
      "ip": "192.168.1.101",
      "port": 8080
    },
    "status": 1,
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00"
  },
  { 
    "id": 3,
    "node_id": 1, 
    "name": "RealSense相机", 
    "description": "RealSense深度相机",
    "category": "Camera", 
    "type": "RealSense", 
    "config": {
      "serial": "427622270438",
      "target_fps": 30
    },
    "status": 0,
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00"
  }
]
```

### GET `/api/devices/{id}`

**获取单个设备详情**

描述：获取单个设备详情。

**路径参数：**
- id: 设备ID

**返回：**

```json
{ 
  "id": 3, 
  "node_id": 1,
  "name": "RealSense相机", 
  "description": "RealSense深度相机", 
  "category": "Camera",
  "type": "RealSense", 
  "config": {
    "serial": "427622270438",
    "target_fps": 30
  },
  "status": 0,
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

### POST `/api/devices`

**新增设备**

描述：新增设备

**请求体 (JSON)：**

```json
{
  "name": "设备名称",
  "node_id": 123,
  "description": "设备描述",
  "category": "VR",
  "type": "VRSocket",
  "config": {
    "ip": "192.168.1.100",
    "port": 12345
  }
}
```

**返回 (状态码：201 Created)：**

```json
{ 
    "message": "设备已添加",
    "id": 3
}
```

### PUT `/api/devices/{id}`

**修改设备配置**

描述：修改设备配置。注意：id、node_id、created_at、updated_at 字段不能通过此接口修改。

**路径参数：**
- id: 设备ID

**请求体 (JSON)：**

```json
{
  "name": "设备名称",
  "description": "设备描述",
  "category": "VR",
  "type": "VRSocket",
  "config": {
    "ip": "192.168.1.100",
    "port": 12346
  }
}
```

**返回：**

```json
{ "message": "配置已更新" }
```

**字段更新限制：**
- id: 禁止修改（系统自动生成）
- node_id: 禁止修改（设备归属节点不可更改）
- created_at: 系统自动生成，禁止用户设置
- updated_at: 系统自动更新，禁止用户指定

### DELETE `/api/devices/{id}`

**删除设备**

描述：彻底删除设备（从数据库移除）。

**路径参数：**
- id: 设备ID

**返回 (状态码：204 No Content)：**

无返回内容

### POST `/api/devices/test`

**测试设备配置**
- 描述：测试设备是否可用

- 请求体（JSON）：
```
{
  "node_id":123,
  "name": "设备名称",
  "description": "设备描述",
  "category": "VR" | "Robot" | "Camera",
  "type": "RealSense",
  "config": {
    "camera_serial": "427622270438"
  }
}
```
- 返回（状态码：200 ）：
```
{ 
    "message": "设备测试成功" 
}
```

## 遥操作组管理

### GET `/api/teleop-groups/types`

**获取遥操组类型信息**

描述：获取遥操组的所有类型和对应的 need_config。注意：由于不同 Node 版本可能不同，所以必须指定 node_id。

**查询参数：**
- node_id: 必选，节点ID

**返回：**

```json
{
  "DefaultTeleopGroup": {
    "name": "默认遥操组",
    "description": "支持双臂+VR+3摄像头的标准配置",
    "need_config": [
      {
        "name": "left_arm",
        "description": "左臂设备",
        "category": "robot"
      },
      {
        "name": "right_arm",
        "description": "右臂设备",
        "category": "Robot"
      },
      {
        "name": "vr",
        "description": "VR设备",
        "category": "VR"
      },
      {
        "name": "camera1",
        "description": "摄像头1",
        "category": "Camera"
      },
      {
        "name": "camera2",
        "description": "摄像头2",
        "category": "Camera"
      },
      {
        "name": "camera3",
        "description": "摄像头3",
        "category": "Camera"
      }
    ]
  }
}
```

### GET `/api/teleop-groups`

**获取遥操作组列表**

描述：获取所有遥操作组列表。

**查询参数 (可选)：**
- name: string - 根据名称模糊匹配过滤结果
- device_id: int - 查询 config 字段包含 device_id 的 teleop-groups
- node_id: int - 筛选 node_id

**返回：**

```json
[
  { 
    "id": 1, 
    "node_id": 1,
    "name": "主操作组",
    "description": "主操作组描述",
    "type": "DefaultTeleopGroup",
    "config": [2,3,7,7,4,8],
    "status": 1,
    "capture_state":0,
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00"
  }
]
```

> config 字段是内部为 device_id 的数组

### GET `/api/teleop-groups/{id}`

**获取单个遥操作组详情**

描述：获取单个遥操作组配置

**路径参数：**
- id: 组ID

**返回：**

```json
{ 
  "id": 1, 
  "node_id": 1,
  "name": "主操作组",
  "description": "主操作组描述",
  "type": "DefaultTeleopGroup",
  "config": [2,3,7,7,4,8],
  "status": 1,
  "capture_state":0,
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

### POST `/api/teleop-groups`

**创建遥操作组**

描述：创建遥操作组

**请求体 (JSON)：**

```json
{ 
  "node_id": 1,
  "name": "主操作组",
  "description": "主操作组描述",
  "type": "DefaultTeleopGroup",
  "config": [2,3,7,7,4,8]
}
```

**返回 (状态码：201 Created)：**

```json
{ 
  "message": "遥操作组已创建",
  "id": 4
}
```

### PUT `/api/teleop-groups/{id}`

**更新遥操作组配置**

描述：更新遥操作组配置。注意：id、node_id、created_at、updated_at 字段不能通过此接口修改。

**路径参数：**
- id: 组ID

**请求体 (JSON)：**

```json
{ 
  "name": "主操作组",
  "description": "主操作组描述",
  "type": "DefaultTeleopGroup",
  "config": [2,3,7,7,4,9],
  "status": 0,
  "capture_state":0
}
```

**返回：**

```json
{ "message": "遥操作组已更新" }
```

**字段更新限制：**
- id: 禁止修改（系统自动生成）
- node_id: 禁止修改（遥操组归属节点不可更改）
- created_at: 系统自动生成，禁止用户设置
- updated_at: 系统自动更新，禁止用户指定

### DELETE `/api/teleop-groups/{id}`

**删除遥操作组**

描述：删除遥操作组。

**路径参数：**
- id: 组ID

**返回 (状态码：204 No Content)：**

无返回内容

### POST `/api/teleop-groups/{id}/start`

**启动遥操作组**

描述：启动遥操作组。启动后系统会根据遥操组类型和配置创建相应的设备实例并启动。

**路径参数：**
- id: 组ID

**返回：**

```json
{ "message": "遥操作已启动" }
```

### POST `/api/teleop-groups/{id}/stop`

**停止遥操作组**

描述：停止遥操作组。停止后系统会释放相关资源并清理状态。

**路径参数：**
- id: 组ID

**返回：**

```json
{ "message": "遥操作已停止" }
```


## 系统架构说明

### 分布式设计原则

1. **职责分离**：
   - Go 后端：配置管理、数据库维护、任务调度
   - Python Node：设备控制、状态管理、实时通信

2. **通信机制**：
   - RESTful API：用于配置管理
   - WebSocket + JSON-RPC：用于实时控制和状态上报

3. **数据一致性**：
   - 所有配置以数据库为唯一数据源
   - 状态变更通过回调机制写入数据库

### 设备管理规范

1. **设备生命周期**：
   - 设备只能通过所属遥操作组启动，不提供单独启动接口
   - 设备状态通过回调接口写入数据库

2. **配置管理**：
   - 设备配置在创建时进行测试验证
   - 配置更新后需要重新测试

### 遥操作组管理规范

1. **类型化配置**：
   - 每个遥操组具有 type 属性标识功能类别
   - 每种类型定义明确的 need_config 配置需求

2. **按需实例化**：
   - 遥操组在用户请求启动时按需实例化
   - 支持实例复用机制

## API 使用规范

### 数据格式

- 所有请求和响应均使用 application/json 格式
- 时间戳格式：ISO 8601 (YYYY-MM-DDTHH:mm:ss)
- 状态码遵循 HTTP 标准规范

### 错误处理

- 4xx 系列错误码表示客户端错误
- 5xx 系列错误码表示服务器错误
- 错误响应格式：{"detail": "错误描述"}

### 安全性

- 所有 API 接口应通过身份验证和授权机制保护
- 敏感操作需要额外权限验证

© 2025 SZUEAILab