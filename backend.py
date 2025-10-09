from fastapi import FastAPI, WebSocket, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import sqlite3
import json
import asyncio
import websockets
from websockets.server import WebSocketServerProtocol
import uuid
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 数据库路径
DB_PATH = "EasyTeleop.db"

# WebSocket连接池
node_websockets: Dict[int, WebSocketServerProtocol] = {}

app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库表
def init_tables(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建 nodes 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid VARCHAR(36) UNIQUE NOT NULL,
            status BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建VR表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vrs(
            uuid VARCHAR(36) PRIMARY KEY,
            device_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES devices(id)
        )
    ''')
    
    # 创建 devices 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            name VARCHAR(20) NOT NULL,
            description TEXT,
            category VARCHAR(20) NOT NULL,
            type VARCHAR(20) NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status INTEGER DEFAULT 0,
            FOREIGN KEY (node_id) REFERENCES nodes (id)
        )
    ''')
    
    # 创建 teleop_groups 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teleop_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            name VARCHAR(20) NOT NULL,
            description TEXT,
            type VARCHAR(20) NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status BOOLEAN DEFAULT 0,
            capture_status BOOLEAN DEFAULT 0,
            FOREIGN KEY (node_id) REFERENCES nodes (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Pydantic模型
class NodeRegisterRequest(BaseModel):
    uuid: str

class NodeRegisterResponse(BaseModel):
    id: int
    devices: List[Dict[str, Any]] = []
    teleop_groups: List[Dict[str, Any]] = []

class NodeResponse(BaseModel):
    id: int
    uuid: str
    status: bool
    created_at: str
    updated_at: str

class DeviceBase(BaseModel):
    name: str
    description: str
    category: str
    type: str
    config: Dict[str, Any]

class DeviceCreate(DeviceBase):
    node_id: int

class DeviceUpdate(DeviceBase):
    name: str
    description: str
    category: str
    type: str
    config: Dict[str, Any]

class DeviceInDB(DeviceBase):
    id: int
    node_id: int
    name: str
    description: str
    category: str
    type: str
    config: Dict[str, Any]
    status: int
    created_at: str
    updated_at: str

class DeviceResponse(BaseModel):
    id: int
    node_id: int
    name: str
    description: str
    category: str
    type: str
    config: Dict[str, Any]
    status: int
    created_at: str
    updated_at: str

class TeleopGroupBase(BaseModel):
    name: str
    description: str
    type: str
    config: List[int]

class TeleopGroupCreate(TeleopGroupBase):
    node_id: int

class TeleopGroupUpdate(TeleopGroupBase):
    pass

class TeleopGroupInDB(TeleopGroupBase):
    id: int
    node_id: int
    status: int
    capture_status: int
    created_at: str
    updated_at: str

class TeleopGroupResponse(BaseModel):
    id: int
    node_id: int
    name: str
    description: str
    type: str
    config: List[int]
    status: int
    capture_status: int
    created_at: str
    updated_at: str

class DeviceTestRequest(DeviceBase):
    """
    设备测试请求模型
    """
    node_id: int = Field(..., description="节点ID")

# 存储等待响应的Future对象，key为websocket对象id和rpc_id的组合
pending_responses: Dict[str, asyncio.Future] = {}

# 添加等待响应的辅助函数
async def wait_for_response(websocket: WebSocketServerProtocol, rpc_id: int, timeout: float = 30.0) -> Any:
    """等待并返回RPC响应结果"""
    # 创建一个Future对象来等待响应
    future = asyncio.Future()
    
    # 生成唯一的键值
    key = f"{id(websocket)}_{rpc_id}"
    
    # 将Future对象存储到pending_responses字典中
    pending_responses[key] = future
    
    try:
        # 等待响应或超时
        response = await asyncio.wait_for(future, timeout=timeout)
        
        # 处理响应，使用更安全的方法避免"string indices must be integers"错误
        if isinstance(response, dict) and 'error' in response:
            error_info = response['error']
            if isinstance(error_info, dict):
                code = error_info.get('code', 'Unknown')
                message = error_info.get('message', 'Unknown error')
                raise Exception(f"RPC Error {code}: {message}")
            else:
                raise Exception(f"RPC Error: {error_info}")
        
        # 安全地返回结果
        if isinstance(response, dict):
            return response.get('result')
        else:
            # 如果响应不是字典，可能需要进一步处理
            return None
    except Exception as e:
        # 确保任何异常都被正确处理
        raise e
    finally:
        # 从pending_responses字典中移除Future对象
        if key in pending_responses:
            del pending_responses[key]

async def handle_jsonrpc_response(message: dict, node_id: int = None):
    """处理JSON-RPC响应"""
    # 处理Node对Backend请求的响应
    print(f"收到Node {node_id} 的响应: {message}")
    
    # 检查是否有人在等待这个响应
    if isinstance(message, dict) and 'id' in message:
        rpc_id = message['id']
        # 遍历所有WebSocket连接查找匹配的等待请求
        for node_id_key, websocket in node_websockets.items():
            key = f"{id(websocket)}_{rpc_id}"
            if key in pending_responses:
                future = pending_responses[key]
                if not future.done():
                    future.set_result(message)
                break

# 节点相关API路由
@app.post("/api/node", response_model=NodeRegisterResponse, status_code=201)
async def register_node(request: NodeRegisterRequest):
    """节点注册API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查节点是否已存在
        cursor.execute("SELECT id FROM nodes WHERE uuid = ?", (request.uuid,))
        result = cursor.fetchone()
        
        if result:
            node_id = result[0]
        else:
            # 创建新节点
            cursor.execute("INSERT INTO nodes (uuid) VALUES (?)", (request.uuid,))
            node_id = cursor.lastrowid
            
        conn.commit()
        
        # 获取该节点的设备和遥操组配置
        devices = get_node_devices(node_id)
        teleop_groups = get_node_teleop_groups(node_id)
        
        return NodeRegisterResponse(
            id=node_id,
            devices=devices,
            teleop_groups=teleop_groups
        )
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

def get_node_devices(node_id: int) -> List[Dict[str, Any]]:
    """获取节点设备配置"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, name, description, category, type, config FROM devices WHERE node_id = ?",
        (node_id,)
    )
    
    devices = []
    for row in cursor.fetchall():
        try:
            config_data = json.loads(row[5]) if isinstance(row[5], str) else row[5]
        except:
            config_data = {}
            
        devices.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "category": row[3],
            "type": row[4],
            "config": config_data
        })
        
    conn.close()
    return devices

def get_node_teleop_groups(node_id: int) -> List[Dict[str, Any]]:
    """获取节点遥操组配置"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, node_id, name, description, type, config FROM teleop_groups WHERE node_id = ?",
        (node_id,)
    )
    
    teleop_groups = []
    for row in cursor.fetchall():
        try:
            config_data = json.loads(row[5]) if isinstance(row[5], str) else row[5]
            # 确保config是列表类型
            if not isinstance(config_data, list):
                config_data = []
        except:
            config_data = []
            
        teleop_groups.append({
            "id": row[0],
            "node_id": row[1],
            "name": row[2],
            "description": row[3],
            "type": row[4],
            "config": config_data
        })
        
    conn.close()
    return teleop_groups

@app.get("/api/nodes", response_model=List[NodeResponse])
async def get_nodes(uuid: Optional[str] = None):
    """获取节点列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if uuid:
        cursor.execute(
            "SELECT id, uuid,status, created_at, updated_at FROM nodes WHERE uuid = ?",
            (uuid,)
        )
    else:
        cursor.execute("SELECT id, uuid,status, created_at, updated_at FROM nodes")
    
    nodes = []
    for row in cursor.fetchall():
        nodes.append(NodeResponse(
            id=row[0],
            uuid=row[1],
            status=row[2],
            created_at=row[3],
            updated_at=row[4]
        ))
        
    conn.close()
    return nodes

@app.get("/api/nodes/{node_id}", response_model=NodeResponse)
async def get_node(node_id: int):
    """获取单个节点详情"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, uuid,status, created_at, updated_at FROM nodes WHERE id = ?",
        (node_id,)
    )
    
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Node not found")
        
    node = NodeResponse(
        id=row[0],
        uuid=row[1],
        status=row[2],
        created_at=row[3],
        updated_at=row[4]
    )
        
    conn.close()
    return node

# 设备相关API路由
@app.get("/api/device/categories")
async def get_device_categories(node_id: int = Query(...)):
    """获取所有设备分类"""
    # 通过RPC从Node获取设备类型信息
    if node_id not in node_websockets:
        raise HTTPException(status_code=404, detail="Node not connected")
        
    try:
        # 直接发送RPC请求，不使用WebSocketRPC
        websocket = node_websockets[node_id]
        rpc_id = int(time.time() * 1000)
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "node.get_device_types",
            "params": {},
            "id": rpc_id
        }
        print(f"asd{json.dumps(rpc_request)}")
        # 发送请求
        await websocket.send_text(json.dumps(rpc_request))
        print("发送成功")
        
        # 等待并处理响应
        device_types_info = await wait_for_response(websocket, rpc_id)
        print(device_types_info)
        categories = list(device_types_info.keys())
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/device/types")
async def get_device_types_info(node_id: int = Query(...)):
    """获取所有设备类型及对应type_info字典"""
    # 通过RPC从Node获取设备类型信息
    if node_id not in node_websockets:
        raise HTTPException(status_code=404, detail="Node not connected")
        
    try:
        # 直接发送RPC请求，不使用WebSocketRPC
        websocket = node_websockets[node_id]
        rpc_id = int(time.time() * 1000)
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "node.get_device_types",
            "params": {},
            "id": rpc_id
        }
        
        # 发送请求
        await websocket.send_text(json.dumps(rpc_request))
        
        # 等待并处理响应
        device_types_info = await wait_for_response(websocket, rpc_id)
        return device_types_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/devices", response_model=List[DeviceResponse])
async def get_devices(node_id: Optional[int] = Query(None)):
    """获取所有设备列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if node_id is not None:
        cursor.execute(
            """SELECT id, node_id, name, description, category, type, config, status, 
                      created_at, updated_at FROM devices WHERE node_id = ?""",
            (node_id,)
        )
    else:
        cursor.execute(
            """SELECT id, node_id, name, description, category, type, config, status, 
                      created_at, updated_at FROM devices"""
        )
    
    devices = []
    for row in cursor.fetchall():
        try:
            config_data = json.loads(row[6]) if isinstance(row[6], str) else row[6]
        except:
            config_data = {}
            
        devices.append(DeviceResponse(
            id=row[0],
            node_id=row[1],
            name=row[2],
            description=row[3],
            category=row[4],
            type=row[5],
            config=config_data,
            status=row[7] or 0,
            created_at=row[8],
            updated_at=row[9]
        ))
        
    conn.close()
    return devices

@app.get("/api/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: int):
    """获取单个设备详情"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT id, node_id, name, description, category, type, config, status, 
                  created_at, updated_at FROM devices WHERE id = ?""",
        (device_id,)
    )
    
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
        
    try:
        config_data = json.loads(row[6]) if isinstance(row[6], str) else row[6]
    except:
        config_data = {}
        
    device = DeviceResponse(
        id=row[0],
        node_id=row[1],
        name=row[2],
        description=row[3],
        category=row[4],
        type=row[5],
        config=config_data,
        status=row[7] or 0,
        created_at=row[8],
        updated_at=row[9]
    )
        
    conn.close()
    return device

@app.post("/api/devices", status_code=201)
async def create_device(device: DeviceCreate):
    """新增设备"""
    # 验证节点是否存在且连接
    if device.node_id not in node_websockets:
        raise HTTPException(status_code=400, detail="Node not connected")
    
    # 对config进行测试，test成功才能创建设备
    # try:
    #     # 直接发送RPC请求，不使用WebSocketRPC
    #     websocket = node_websockets[device.node_id]
    #     rpc_id = int(time.time() * 1000)
    #     rpc_request = {
    #         "jsonrpc": "2.0",
    #         "method": "node.test_device",
    #         "params": {
    #             "category": device.category,
    #             "type": device.type,
    #             "config": device.config
    #         },
    #         "id": rpc_id
    #     }
        
    #     # 发送请求
    #     await websocket.send_text(json.dumps(rpc_request))
        
    #     # 等待并处理响应
    #     test_result = await wait_for_response(websocket, rpc_id)
        
    #     # 检查测试结果，确保test_result是字典类型
    #     if not isinstance(test_result, dict) or test_result.get("success") is not True:
    #         error_msg = test_result.get("error", "Device test failed") if isinstance(test_result, dict) else "Device test failed"
    #         raise HTTPException(status_code=400, detail=error_msg)
    # except asyncio.TimeoutError:
    #     raise HTTPException(status_code=504, detail="Device test timeout")
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Device test error: {str(e)}")
    
    # 在数据库中创建设备
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """INSERT INTO devices (node_id, name, description, category, type, config) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (device.node_id, device.name, device.description, device.category, 
             device.type, json.dumps(device.config))
        )
        device_id = cursor.lastrowid
        conn.commit()
        
        # 通知对应的Node更新配置
        await notify_node_config_update(device.node_id)
        
        # 返回标准化的响应
        return {
            "message": "设备已添加", 
            "id": device_id,
            "device_id": device_id
        }
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Database constraint error: {str(e)}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/api/devices/{device_id}")
async def update_device(device_id: int, device: DeviceUpdate):
    """更新设备"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查设备是否存在
        cursor.execute("SELECT id, node_id FROM devices WHERE id = ?", (device_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Device not found")
            
        node_id = row[1]
        
        # # 对config进行测试，test成功才能更新设备
        # if node_id not in node_websockets:
        #     raise HTTPException(status_code=400, detail="Node not connected")
        
        # try:
        #     # 直接发送RPC请求，不使用WebSocketRPC
        #     websocket = node_websockets[node_id]
        #     rpc_id = int(time.time() * 1000)
        #     rpc_request = {
        #         "jsonrpc": "2.0",
        #         "method": "node.test_device",
        #         "params": {
        #             "category": device.category,
        #             "type": device.type,
        #             "config": device.config
        #         },
        #         "id": rpc_id
        #     }
            
        #     # 发送请求
        #     await websocket.send_text(json.dumps(rpc_request))
            
        #     # 等待并处理响应
        #     test_result = await wait_for_response(websocket, rpc_id)
            
        #     # 检查测试结果，确保test_result是字典类型
        #     if not isinstance(test_result, dict) or test_result.get("success") is not True:
        #         raise HTTPException(status_code=400, detail="Device test failed")
        # except Exception as e:
        #     raise HTTPException(status_code=500, detail=f"Device test error: {str(e)}")
        
        # 更新设备信息
        cursor.execute(
            """UPDATE devices 
               SET name = ?, description = ?, category = ?, type = ?, config = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (device.name, device.description, device.category, device.type, 
             json.dumps(device.config), device_id)
        )
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Device not found")
            
        conn.commit()
        
        # 通知对应的Node更新配置
        await notify_node_config_update(node_id)
        
        return {"message": "设备已更新"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: int):
    """删除设备"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查设备是否存在并获取node_id
        cursor.execute("SELECT id, node_id FROM devices WHERE id = ?", (device_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Device not found")
            
        node_id = row[1]
        
        # 删除设备
        cursor.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Device not found")
            
        conn.commit()
        
        # 通知对应的Node更新配置
        await notify_node_config_update(node_id)
        
        return {"message": "设备已删除"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/devices/test", description="测试设备连接")
async def test_device_connection(device_test_request: DeviceTestRequest):
    """
    测试设备连接
    
    该端点用于测试指定设备是否能成功连接。需要提供节点ID、设备类别、设备类型和设备配置参数。
    
    示例请求体:
    {
        "node_id": 1,
        "category": "robot", 
        "type": "RealMan",
        "config": {
            "ip": "192.168.1.100",
            "port": 8080
        }
    }
    """
    node_id = device_test_request.node_id
    category = device_test_request.category
    type_name = device_test_request.type
    config = device_test_request.config
    # 验证节点是否存在且连接
    if node_id not in node_websockets:
        raise HTTPException(status_code=400, detail="Node not connected")
    
    try:
        # 直接发送RPC请求，不使用WebSocketRPC
        websocket = node_websockets[node_id]
        rpc_id = int(time.time() * 1000)
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "node.test_device",
            "params": {
                "category": category,
                "type": type_name,
                "config": config
            },
            "id": rpc_id
        }
        
        # 发送请求
        await websocket.send_text(json.dumps(rpc_request))
        
        # 等待并处理响应
        test_result = await wait_for_response(websocket, rpc_id)
        
        # 检查测试结果，确保test_result是字典类型
        if not isinstance(test_result, dict) or test_result.get("success") is not True:
            raise HTTPException(status_code=400, detail="Device test failed")
            
        return test_result
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Device test timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Device test error: {str(e)}")

# 遥操组相关API路由
@app.get("/api/teleop-groups/types")
async def get_teleop_group_types_info(node_id: int = Query(...)):
    """获取遥操组的所有类型和对应的need_config"""
    # 通过RPC从Node获取遥操组类型信息
    if node_id not in node_websockets:
        raise HTTPException(status_code=404, detail="Node not connected")
        
    try:
        # 直接发送RPC请求，不使用WebSocketRPC
        websocket = node_websockets[node_id]
        rpc_id = int(time.time() * 1000)
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "node.get_teleop_group_types",
            "params": {},
            "id": rpc_id
        }
        
        # 发送请求
        await websocket.send_text(json.dumps(rpc_request))
        
        # 等待并处理响应
        teleop_group_types_info = await wait_for_response(websocket, rpc_id)
        return teleop_group_types_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/teleop-groups", response_model=List[TeleopGroupResponse])
async def get_teleop_groups(
    name: Optional[str] = Query(None),
    device_id: Optional[int] = Query(None),
    node_id: Optional[int] = Query(None)
):
    """获取所有遥操作组列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 构造查询语句
    query = """SELECT id, node_id, name, description, type, config, status,capture_status, 
                      created_at, updated_at FROM teleop_groups"""
    params = []
    
    conditions = []
    if name:
        conditions.append("name LIKE ?")
        params.append(f"%{name}%")
    if node_id is not None:
        conditions.append("node_id = ?")
        params.append(node_id)
    if device_id is not None:
        conditions.append("config LIKE ?")
        params.append(f"%{device_id}%")
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY id"
    
    cursor.execute(query, params)
    
    groups = []
    for row in cursor.fetchall():
        try:
            config_data = json.loads(row[5]) if isinstance(row[5], str) else row[5]
            # 确保config是列表类型
            if not isinstance(config_data, list):
                config_data = []
        except:
            config_data = []
            
        groups.append(TeleopGroupResponse(
            id=row[0],
            node_id=row[1],
            name=row[2],
            description=row[3],
            type=row[4],
            config=config_data,
            status=row[6],
            capture_status=row[7],
            created_at=row[8],
            updated_at=row[9]
        ))
        
    conn.close()
    return groups

@app.get("/api/teleop-groups/{id}", response_model=TeleopGroupResponse)
async def get_teleop_group(id: int):
    """获取单个遥操组详情"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT id, node_id, name, description, type, config, status,capture_status, 
                  created_at, updated_at FROM teleop_groups WHERE id = ?""",
        (id,)
    )
    
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Teleop group not found")
        
    try:
        config_data = json.loads(row[5]) if isinstance(row[5], str) else row[5]
        # 确保config是列表类型
        if not isinstance(config_data, list):
            config_data = []
    except:
        config_data = []
        
    teleop_group = TeleopGroupResponse(
        id=row[0],
        node_id=row[1],
        name=row[2],
        description=row[3],
        type=row[4],
        config=config_data,
        status=row[6],
        capture_status=row[7],
        created_at=row[8],
        updated_at=row[9]
    )
        
    conn.close()
    return teleop_group

@app.post("/api/teleop-groups", status_code=201)
async def create_teleop_group(group: TeleopGroupCreate):
    """新增遥操组"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 验证节点是否存在
        cursor.execute("SELECT id FROM nodes WHERE id = ?", (group.node_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Node not found")
            
        cursor.execute(
            """INSERT INTO teleop_groups (node_id, name, description, type, config) 
               VALUES (?, ?, ?, ?, ?)""",
            (group.node_id, group.name, group.description, group.type, 
             json.dumps(group.config))
        )
        id = cursor.lastrowid
        conn.commit()
        
        # 通知对应的Node更新配置
        await notify_node_config_update(group.node_id)
        
        return {"message": "遥操组已添加", "id": id}
        
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/api/teleop-groups/{id}")
async def update_teleop_group(id: int, group: TeleopGroupUpdate):
    """更新遥操组"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查遥操组是否存在并获取node_id
        cursor.execute("SELECT id, node_id FROM teleop_groups WHERE id = ?", (id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Teleop group not found")
            
        node_id = row[1]
        
        # 如果没有提供status，则不更新status
        cursor.execute(
            """UPDATE teleop_groups SET name=?, description=?, type=?, config=?, updated_at=datetime('now') 
                WHERE id = ?""",
            (group.name, group.description, group.type, json.dumps(group.config), id)
        )
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Teleop group not found")
            
        conn.commit()
        
        # 通知对应的Node更新配置
        await notify_node_config_update(node_id)
        
        return {"message": "遥操组已更新"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/teleop-groups/{id}/start")
async def start_teleop_group(id: int):
    """启动遥操组"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取遥操组信息
    cursor.execute(
        """SELECT id, node_id, name, description, type, config, status 
           FROM teleop_groups WHERE id = ?""",
        (id,)
    )
    
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Teleop group not found")
        
    node_id = row[1]
    if node_id not in node_websockets:
        raise HTTPException(status_code=400, detail="Node not connected")
        
    try:
        # 发送启动遥操组的RPC请求
        websocket = node_websockets[node_id]
        rpc_id = int(time.time() * 1000)
        config_data = json.loads(row[5]) if isinstance(row[5], str) else row[5]
        # 确保config是列表类型
        if not isinstance(config_data, list):
            config_data = []
        
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "node.start_teleop_group",
            "params": {
                "id": id,
                # "config": config_data
            },
            "id": rpc_id
        }
        
        # 发送请求
        await websocket.send_text(json.dumps(rpc_request))
        
        # 等待并处理响应
        result = await wait_for_response(websocket, rpc_id)
        
        # 检查结果，确保result是字典类型
        if not isinstance(result, dict) or result.get("success") is not True:
            raise HTTPException(status_code=400, detail="Failed to start teleop group")
            
        # 更新数据库中的状态
        cursor.execute(
            "UPDATE teleop_groups SET status = 1, updated_at = datetime('now') WHERE id = ?",
            (id,)
        )
        conn.commit()
        
        return {"message": "遥操组已启动"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/teleop-groups/{id}/stop")
async def stop_teleop_group(id: int):
    """停止遥操作组"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取遥操组信息
    cursor.execute(
        """SELECT id, node_id, name, description, type, config, status 
           FROM teleop_groups WHERE id = ?""",
        (id,)
    )
    
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Teleop group not found")
        
    node_id = row[1]
    if node_id not in node_websockets:
        raise HTTPException(status_code=400, detail="Node not connected")
        
    try:
        # 发送启动遥操组的RPC请求
        websocket = node_websockets[node_id]
        rpc_id = int(time.time() * 1000)
        
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "node.stop_teleop_group",
            "params": {
                "id": id,
            },
            "id": rpc_id
        }
        
        # 发送请求
        await websocket.send_text(json.dumps(rpc_request))
        
        # 等待并处理响应
        result = await wait_for_response(websocket, rpc_id)
        
        # 检查结果，确保result是字典类型
        if not isinstance(result, dict) or result.get("success") is not True:
            raise HTTPException(status_code=400, detail="Failed to stop teleop group")
            
        # 更新数据库中的状态
        cursor.execute(
            "UPDATE teleop_groups SET status = 0, updated_at = datetime('now') WHERE id = ?",
            (id,)
        )
        conn.commit()
        
        return {"message": "遥操组已停止动"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/teleop-groups/{id}", status_code=204)
async def delete_teleop_group(id: int):
    """删除遥操作组"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 获取node_id用于通知
        cursor.execute("SELECT node_id FROM teleop_groups WHERE id = ?", (id,))
        row = cursor.fetchone()
        
        cursor.execute("DELETE FROM teleop_groups WHERE id = ?", (id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Teleop group not found")
            
        conn.commit()
        
        if row:
            # 通知对应的Node更新配置
            await notify_node_config_update(row[0])
            
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# 通知相关函数
async def notify_node_config_update(node_id: int):
    """通知Node更新配置"""
    if node_id in node_websockets:
        websocket = node_websockets[node_id]
        
        # 创建配置更新通知
        notification = {
            "jsonrpc": "2.0",
            "method": "node.update_config",
            "params": {}
        }
        
        try:
            await websocket.send_text(json.dumps(notification))
        except Exception as e:
            print(f"通知Node {node_id} 更新配置失败: {e}")

async def notify_node_start_teleop_group(node_id: int, id: int):
    """通知Node启动遥操组"""
    if node_id in node_websockets:
        websocket = node_websockets[node_id]
        
        # 创建启动遥操组通知
        notification = {
            "jsonrpc": "2.0",
            "method": "node.start_teleop_group",
            "params": {
                "id": id
            }
        }
        
        try:
            # 发送通知
            if websocket.state.name != 'CLOSED':
                await websocket.send_text(json.dumps(notification))
        except Exception as e:
            print(f"通知Node {node_id} 启动遥操组 {id} 失败: {e}")

async def notify_node_stop_teleop_group(node_id: int, id: int):
    """通知Node停止遥操组"""
    if node_id in node_websockets:
        websocket = node_websockets[node_id]
        
        # 创建停止遥操组通知
        notification = {
            "jsonrpc": "2.0",
            "method": "node.stop_teleop_group",
            "params": {
                "id": id
            }
        }
        
        try:
            # 发送通知
            if websocket.state.name != 'CLOSED':
                await websocket.send_text(json.dumps(notification))
        except Exception as e:
            print(f"通知Node {node_id} 停止遥操组 {id} 失败: {e}")

# WebSocket端点
@app.websocket("/ws/rpc")
async def websocket_endpoint(websocket: WebSocket):
    """处理Node的WebSocket连接"""
    await websocket.accept()
    
    node_id = None
    try:
        # 建立连接后主动询问节点ID
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "node.get_node_id",
            "params": {},
            "id": int(time.time() * 1000)  # 使用时间戳作为请求ID
        }
        await websocket.send_text(json.dumps(rpc_request))
        
        # 等待节点响应
        data = await websocket.receive_text()
        message = json.loads(data)
        
        # 处理节点ID响应
        if "id" in message and "result" in message and isinstance(message["result"], dict) and "id" in message["result"]:
            node_id = message["result"]["id"]
            if node_id:
                # 保存WebSocket连接
                node_websockets[node_id] = websocket
                print(f"Node {node_id} connected and added to connection pool")
                
                # 更新数据库中节点的状态为在线(1)
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE nodes SET status = 1, updated_at = datetime('now') WHERE id = ?",
                        (node_id,)
                    )
                    conn.commit()
                    conn.close()
                    print(f"Node {node_id} status updated to online in database")
                except Exception as e:
                    print(f"Failed to update node {node_id} status in database: {e}")
        
        # 继续处理后续消息
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理JSON-RPC请求
            if "method" in message:
                response = await handle_jsonrpc_request(message, websocket, node_id)
                if response:
                    await websocket.send_text(json.dumps(response))
            
            # 处理JSON-RPC响应
            elif "id" in message and ("result" in message or "error" in message):
                await handle_jsonrpc_response(message, node_id)
                
    except Exception as e:
        print(f"WebSocket连接错误: {e}")
    finally:
        # 清理连接的节点
        if node_id and node_id in node_websockets:
            del node_websockets[node_id]
            print(f"Node {node_id} disconnected and removed from connection pool")
            
            # 更新数据库中节点的状态为离线(0)
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE nodes SET status = 0, updated_at = datetime('now') WHERE id = ?",
                    (node_id,)
                )
                conn.commit()
                conn.close()
                print(f"Node {node_id} status updated to offline in database")
            except Exception as e:
                print(f"Failed to update node {node_id} status in database: {e}")

async def handle_jsonrpc_request(request: dict, websocket: WebSocket, node_id: int = None) -> dict:
    """处理JSON-RPC请求"""
    rpc_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})
    
    response = {
        "jsonrpc": "2.0",
        "id": rpc_id
    }
    
    try:
        # 处理Node提供的方法（node.开头的方法由Node实现，Backend调用）
        if method == "node.register":
            # Node向Backend注册
            result = await handle_node_register(params, websocket)
            response["result"] = result
            # 更新node_id
            if isinstance(result, dict) and "id" in result:
                node_id = result["id"]
                # 保存WebSocket连接
                if node_id:
                    node_websockets[node_id] = websocket
        elif method == "node.test_device":
            # Backend要求Node测试设备（响应）
            result = await handle_node_test_device(params)
            response["result"] = result
        else:
            response["error"] = {
                "code": -32601,
                "message": "Method not found"
            }
    except Exception as e:
        response["error"] = {
            "code": -32603,
            "message": str(e)
        }
    
    return response

async def handle_node_register(params: dict, websocket: WebSocket) -> dict:
    """处理Node注册"""
    node_uuid = params.get("uuid")
    
    if not node_uuid:
        raise Exception("Missing uuid parameter")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查节点是否已存在
        cursor.execute("SELECT id FROM nodes WHERE uuid = ?", (node_uuid,))
        result = cursor.fetchone()
        
        if result:
            node_id = result[0]
        else:
            # 创建新节点
            cursor.execute("INSERT INTO nodes (uuid) VALUES (?)", (node_uuid,))
            node_id = cursor.lastrowid
            
        conn.commit()
        
        # 保存WebSocket连接
        node_websockets[node_id] = websocket
        
        return {"id": node_id}
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

async def handle_node_test_device(params: dict) -> int:
    """处理Node设备测试请求"""
    category = params.get("category")
    type_name = params.get("type")
    config = params.get("config")
    
    # 这里应该根据设备类型进行实际测试
    # 目前简化处理，直接返回测试成功
    print(f"Testing device: {category}.{type_name} with config {config}")
    
    # 模拟测试过程需要几秒钟
    await asyncio.sleep(3)
    
    return 1  # 测试成功

# 挂载静态文件夹
app.mount("/", StaticFiles(directory="static"), name="static")
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/index.html")
# 启动时初始化数据库
@app.on_event("startup")
async def startup_event():
    init_tables(DB_PATH)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)