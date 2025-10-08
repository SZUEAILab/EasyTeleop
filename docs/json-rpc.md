Node提供的RPC工具
获取node_id
建立ws连接后后端需要向node询问id从而将ws连接放入连接池中
Request:
{
  "jsonrpc": "2.0",
  "method": "node.get_node_id",
  "params": {
    
  },
  "id": 1
}

Response:
{
  "jsonrpc": "2.0",
  "result": {
      "id":1
  },
  "id": 1
}
获取设备type配置
Node通过调用Device模块的get_device_types方法动态获取category和type以及对应的need_config
Request:
{
  "jsonrpc": "2.0",
  "method": "node.get_device_types",
  "params": {
    
  },
  "id": 1
}

Response:
{
  "jsonrpc": "2.0",
  "result": {
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
  },
  "id": 1
}
获取遥操组type配置
Node通过调用TeleopGroup模块的get_teleop_group_types方法动态获取category和type以及对应的need_config
Request:
{
  "jsonrpc": "2.0",
  "method": "node.get_teleop_group_types",
  "params": {
    
  },
  "id": 1
}

Response:
{
  "jsonrpc": "2.0",
  "result": {
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
            "category": "robot"
          },
          {
            "name": "vr",
            "description": "VR设备",
            "category": "vr"
          },
          {
            "name": "camera1",
            "description": "摄像头1",
            "category": "camera"
          },
          {
            "name": "camera2",
            "description": "摄像头2",
            "category": "camera"
          },
          {
            "name": "camera3",
            "description": "摄像头3",
            "category": "camera"
          }
        ]
      }
  },
  "id": 1
}
设备测试
后端添加设备后通知Node运行测试代码，判断设备是否正常连接，Node返回测试阶段，中间需要等待几秒
Request:
{
  "jsonrpc": "2.0",
  "method": "node.test_device",
  "params": {
    "category":"robot",
    "type":"realman",
    "config":{
        "ip":"192.16.0.1"
    }
  },
  "id": 1
}

Response:
{
  "jsonrpc": "2.0",
  "result": 1,
  "id": 1
}
配置刷新
当后端修改了设备或者遥操组时会通知Node刷新配置，Node需要清空devices_pool和teleop_groups_pool并发送GET api/devices?node_id=1和GET api/teleop-groups?node_id=1来获取新配置
Notification:
{
  "jsonrpc": "2.0",
  "method": "node.update_config",
  "params": {
    
  },
}
启动遥操组
后端向Node发送启动/停止遥操组的命令
Notification:
{
  "jsonrpc": "2.0",
  "method": "node.start_teleop-group",
  "params": {
    "id":5
  },
}
停止遥操组
Notification:
{
  "jsonrpc": "2.0",
  "method": "node.start_teleop-group",
  "params": {
    "id":5
  },
}