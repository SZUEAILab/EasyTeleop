import asyncio
import json
import uuid
import os
from typing import Dict, Any, List
import requests
import time
import logging

from Components.WebSocketRPC import WebSocketRPC
from Device import get_device_types, get_device_classes
from TeleopGroup import get_teleop_group_types, get_teleop_group_classes

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class Node:
    def __init__(self, backend_url: str = "http://localhost:8000",websocket_uri: str = "ws://localhost:8000/ws/rpc"):
        self.backend_url = backend_url
        self.node_id = None
        self.websocket_rpc = WebSocketRPC()
        
        self.websocket_uri = websocket_uri
        
        self.devices_config = []
        self.teleop_groups_config = []
        self.devices_pool: Dict[int, Any] = {}
        self.teleop_groups_pool: Dict[int, Any] = {}
        # 获取设备类型和遥操组类型配置
        self.device_types = get_device_types()
        self.device_classes = get_device_classes()
        self.teleop_group_types = get_teleop_group_types()
        self.teleop_group_classes = get_teleop_group_classes()
        
        # 注册RPC方法
        self._register_rpc_methods()
        
    def _register_rpc_methods(self):
        """注册Node端需要实现的RPC方法"""
        self.websocket_rpc.register_method("node.test_device", self.test_device)
        self.websocket_rpc.register_method("node.update_config", self.update_config)
        self.websocket_rpc.register_method("node.start_teleop_group", self.start_teleop_group)
        self.websocket_rpc.register_method("node.stop_teleop_group", self.stop_teleop_group)
        self.websocket_rpc.register_method("node.get_device_types", self.get_device_types)
        self.websocket_rpc.register_method("node.get_teleop_group_types", self.get_teleop_group_types)
        self.websocket_rpc.register_method("node.get_node_id", self.get_node_id)
        
    async def get_node_id(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取节点ID
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
        """
        return {"id": self.node_id} if self.node_id else {"id": None}
        
    async def test_device(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        测试设备连接
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
        """
        print(f"开始测试设备: {params}")
        
        # 确保params是字典类型
        if not isinstance(params, dict):
            return {"success": False, "message": "Invalid params format"}
        
        category = params.get("category")
        type_name = params.get("type")
        config = params.get("config")
        
        # 获取设备类
        if category not in self.device_classes or type_name not in self.device_classes[category]:
            return {"success": False, "message": f"Unsupported device type: {category}.{type_name}"}
            
        device_class = self.device_classes[category][type_name]
        
        try:
            # 实例化设备
            device = device_class(config)
            
            # 启动设备
            device.start()
            
            # 等待设备连接状态变为1（已连接），超时时间2秒
            start_time = time.time()
            while time.time() - start_time < 2.0:
                if device.get_conn_status() == 1:  # 已连接
                    device.stop()  # 测试完成后停止设备
                    return {"success": True, "message": "Device connected successfully"}
                await asyncio.sleep(0.1)  # 短暂休眠避免过度占用CPU
                
            # 超时处理
            device.stop()  # 停止设备
            return {"success": False, "message": "Device connection timeout"}
            
        except Exception as e:
            return {"success": False, "message": f"Device test failed: {str(e)}"}
        
    async def update_config(self, params: Dict[str, Any] = None) -> None:
        """
        更新配置
        Notification:
        {
          "jsonrpc": "2.0",
          "method": "node.update_config",
          "params": {},
        }
        """
        print("收到配置更新通知，正在清空设备池和遥操组池...")
        
        # 停止所有正在运行的遥操组
        for group_id, group_instance in self.teleop_groups_pool.items():
            if hasattr(group_instance, 'running') and group_instance.running:
                group_instance.stop()
        
        # 停止所有设备并清空设备池
        for device_id, device_instance in self.devices_pool.items():
            if hasattr(device_instance, 'stop'):
                device_instance.stop()
        
        # 清空设备池和遥操组池
        self.devices_pool.clear()
        self.teleop_groups_pool.clear()
        
        # 从后端获取新配置
        if self.node_id:
            await self._fetch_devices_config()
            await self._fetch_teleop_groups_config()
            
            # 根据新配置初始化设备和遥操组
            await self._initialize_devices()
            
        print("配置更新完成")
        
    async def start_teleop_group(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        启动遥操组
        Notification:
        {
          "jsonrpc": "2.0",
          "method": "node.start_teleop_group",
          "params": {
            "id":5
          },
        }
        """
        group_id = params.get("id")
        print(f"正在启动遥操组 {group_id}")
        
        # 检查遥操组是否存在
        group_config = None
        for config in self.teleop_groups_config:
            if config.get("id") == group_id:
                group_config = config
                break
        
        if group_config is None:
            return {"success": False, "message": f"Teleop group {group_id} not found"}
            
        # 获取遥操组配置
        group_devices_config = group_config.get("config")
        
        # 获取遥操组类
        group_type = group_config.get("type")
        
        if group_type not in self.teleop_group_classes:
            return {"success": False, "message": f"Teleop group type {group_type} not supported"}
            
        # 构建设备对象列表
        device_objects = []
        for device_id in group_devices_config:
            if device_id in self.devices_pool:
                device_objects.append(self.devices_pool[device_id])
            else:
                device_objects.append(None)
        
        # 实例化遥操组
        group_class = self.teleop_group_classes[group_type]
        teleop_group_instance = group_class(device_objects)
        
        # 启动遥操组
        success = teleop_group_instance.start()
        
        if success:
            # 更新遥操组池中的实例
            self.teleop_groups_pool[group_id] = teleop_group_instance
            return {"success": True, "message": f"Teleop group {group_id} started successfully"}
        else:
            return {"success": False, "message": f"Failed to start teleop group {group_id}"}

    async def stop_teleop_group(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        停止遥操组
        Notification:
        {
          "jsonrpc": "2.0",
          "method": "node.stop_teleop_group",
          "params": {
            "id":5
          },
        }
        """
        group_id = params.get("id")
        print(f"停止遥操组 {group_id}")
        
        # 检查遥操组是否存在
        group_exists = any(config.get("id") == group_id for config in self.teleop_groups_config)
        if not group_exists:
            return {"success": False, "message": f"Teleop group {group_id} not found"}
        # 检测是否启动
        if group_id not in self.teleop_groups_pool:
            return {"success": False, "message": f"Teleop group {group_id} not start"}
            
        group_instance = self.teleop_groups_pool[group_id]
        
        # 检查是否为运行中的遥操组实例
        if not hasattr(group_instance, 'running') or not group_instance.running:
            del self.teleop_groups_pool[group_id]
            return {"success": False, "message": f"Teleop group {group_id} is not running"}
        
        # 停止遥操组
        success = group_instance.stop()
        
        if success:
            # 从遥操组池中移除实例
            del self.teleop_groups_pool[group_id]
            return {"success": True, "message": f"Teleop group {group_id} stopped successfully"}
        else:
            return {"success": False, "message": f"Failed to stop teleop group {group_id}"}
        
    async def get_device_types(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取设备类型配置
        Request:
        {
          "jsonrpc": "2.0",
          "method": "node.get_device_types",
          "params": {},
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
              }
          },
          "id": 1
        }
        """
        return self.device_types
        
    async def get_teleop_group_types(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取遥操组类型配置
        Request:
        {
          "jsonrpc": "2.0",
          "method": "node.get_teleop_group_types",
          "params": {},
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
                    "describe": "左臂设备",
                    "category": "robot"
                  },
                  {
                    "name": "right_arm",
                    "describe": "右臂设备",
                    "category": "robot"
                  },
                  {
                    "name": "vr",
                    "describe": "VR设备",
                    "category": "vr"
                  },
                  {
                    "name": "camera1",
                    "describe": "摄像头1",
                    "category": "camera"
                  },
                  {
                    "name": "camera2",
                    "describe": "摄像头2",
                    "category": "camera"
                  },
                  {
                    "name": "camera3",
                    "describe": "摄像头3",
                    "category": "camera"
                  }
                ]
              }
          },
          "id": 1
        }
        """
        return self.teleop_group_types
        
    def _get_device_class_by_type(self, category: str, type_name: str):
        """根据设备类别和类型获取设备类"""
        if category in self.device_classes and type_name in self.device_classes[category]:
            return self.device_classes[category][type_name]
        return None
        
    async def _initialize_devices(self):
        """根据设备配置初始化设备对象并放入设备池"""
        print("初始化设备...")
        
        for device_config in self.devices_config:
            # 获取设备类别和类型
            device_id = device_config.get("id")
            category = device_config.get("category")
            type = device_config.get("type")
            config = device_config.get("config", {})
            
            # 获取设备类
            device_class = self._get_device_class_by_type(category, type)
            if not device_class:
                print(f"无法找到设备类: {category}.{type}")
                continue
                
            try:
                # 实例化设备
                device_instance = device_class(config)
                
                # 将设备实例放入设备池
                self.devices_pool[device_id] = device_instance
                
                print(f"设备 {device_id} ({category}.{type}) 初始化成功")
            except Exception as e:
                print(f"设备 {device_id} ({category}.{type}) 初始化失败: {e}")
        
        print("所有设备初始化完成")
        
    def get_or_create_node_uuid(self) -> str:
        """获取或创建节点UUID"""
        uuid_file = "node_uuid.txt"
        if os.path.exists(uuid_file):
            with open(uuid_file, "r") as f:
                return f.read().strip()
        else:
            new_uuid = str(uuid.uuid4())
            with open(uuid_file, "w") as f:
                f.write(new_uuid)
            return new_uuid
            
    async def register_node(self) -> Dict[str, Any]:
        """向后端注册节点"""
        node_uuid = self.get_or_create_node_uuid()
        
        # 发送注册请求
        register_data = {
            "uuid": node_uuid
        }
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/node",
                json=register_data
            )
            
            if response.status_code == 201:
                result = response.json()
                self.node_id = result.get("id")
                print(f"节点注册成功，ID: {self.node_id}")
                
                # 获取初始配置
                await self._fetch_devices_config()
                await self._fetch_teleop_groups_config()
                
                # 初始化设备
                await self._initialize_devices()
                
                return result
            else:
                raise Exception(f"节点注册失败: {response.text}")
                
        except Exception as e:
            print(f"节点注册出错: {e}")
            raise
            
        
    async def _fetch_devices_config(self):
        """获取设备配置"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/devices",
                params={"node_id": self.node_id}
            )
            
            if response.status_code == 200:
                devices = response.json()
                print(f"获取到 {len(devices)} 个设备配置")
                self.devices_config =  devices
            else:
                print(f"获取设备配置失败: {response.text}")
                self.devices_config = []
                
        except Exception as e:
            print(f"获取设备配置出错: {e}")
            self.devices_config = []
            
    async def _fetch_teleop_groups_config(self):
        """获取遥操组配置"""
        try:
            response = requests.get(
                f"{self.backend_url}/api/teleop-groups",
                params={"node_id": self.node_id}
            )
            
            if response.status_code == 200:
                groups = response.json()
                print(f"获取到 {len(groups)} 个遥操组配置")
                self.teleop_groups_config = groups
            else:
                print(f"获取遥操组配置失败: {response.text}")
                self.teleop_groups_config = []
                
        except Exception as e:
            print(f"获取遥操组配置出错: {e}")
            self.teleop_groups_config = []
            
    async def connect_to_backend(self):
        """连接到后端"""
        if not self.node_id:
            raise Exception("节点未注册，请先调用register_node()")
            
        print("正在连接到后端...")
        await self.websocket_rpc.connect(self.websocket_uri)


# 运行节点示例
async def main():
    # 创建节点实例
    node = Node(backend_url="http://121.43.162.224:8000", websocket_uri="ws://121.43.162.224:8000/ws/rpc")
    # node = Node()
    
    try:
        # 注册节点
        await node.register_node()
        
        # 连接到后端
        await node.connect_to_backend()
        
    except KeyboardInterrupt:
        print("节点已停止")
    except Exception as e:
        print(f"节点运行出错: {e}")


if __name__ == "__main__":
    asyncio.run(main())