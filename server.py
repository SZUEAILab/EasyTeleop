import yaml
from fastapi import FastAPI, HTTPException, Body, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, RootModel
from typing import Optional, List, Dict, Union, Any
import threading
import uvicorn  # 导入uvicorn
import sqlite3
import os
import json
from contextlib import asynccontextmanager

from TeleopGroup import get_teleop_group_types, get_teleop_group_classes
from Device import get_device_classes, get_device_types

# 设备类型配置（动态获取）
DEVICE_CLASSES = get_device_classes()
DEVICE_TYPES = get_device_types()

DB_PATH = "teleop_data.db"

# 遥操作组管理
TELEOP_GROUPS = {}

# 遥操作组类型配置（动态获取）
TELEOP_GROUP_TYPES = get_teleop_group_types()
TELEOP_GROUP_CLASSES = get_teleop_group_classes()

def parse_device_id(device_id):
    """Helper function to parse device ID from config"""
    if device_id is None:
        return None
    if isinstance(device_id, str) and device_id.isdigit():
        return int(device_id)
    return device_id if isinstance(device_id, int) else None




def init_tables(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建 nodes 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid VARCHAR(36) UNIQUE NOT NULL,
            status BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建 devices 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            name VARCHAR(20) NOT NULL,
            description TEXT NOT NULL,
            category VARCHAR(20) NOT NULL,
            type VARCHAR(20) NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status INTEGER DEFAULT 0,
            FOREIGN KEY (node_id) REFERENCES nodes (id)
        )
    ''')
    
    # 创建遥操组表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teleop_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(20) NOT NULL,
            description TEXT,
            type VARCHAR(20) NOT NULL,
            config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# 获取数据库连接
def get_db_conn():
    db_path = os.path.join(os.path.dirname(__file__), "teleop_data.db")
    return sqlite3.connect(db_path)

# Pydantic模型定义
class DeviceBase(BaseModel):
    name: str
    description: str
    category: str
    type: str
    config: dict

class DeviceCreate(BaseModel):
    name: str
    description: str
    category: str
    type: str
    config: dict

class DeviceCreateResponse(BaseModel):
    message: str
    id: int

class DeviceUpdate(BaseModel):
    config: dict
    category: Optional[str] = None

class Device(BaseModel):
    id: int
    name: str
    description: str
    category: str
    type: str
    config: dict

    class Config:
        from_attributes = True

class DeviceStatusResponse(BaseModel):
    conn_status: int

class DeviceCategoryResponse(BaseModel):
    categories: List[str]

class DeviceTypeConfigResponse(RootModel[Dict[str, List[str]]]):
    # 适配Pydantic V2，使用RootModel
    pass

class TeleopGroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    left_arm_id: Optional[int] = None
    right_arm_id: Optional[int] = None
    vr_id: Optional[int] = None
    camera1_id: Optional[int] = None
    camera2_id: Optional[int] = None
    camera3_id: Optional[int] = None

class TeleopGroupCreate(TeleopGroupBase):
    pass

class TeleopGroupCreateResponse(BaseModel):
    message: str
    id: str

class TeleopGroupUpdate(TeleopGroupBase):
    name: Optional[str] = None
    description: Optional[str] = None
    left_arm_id: Optional[int] = None
    right_arm_id: Optional[int] = None
    vr_id: Optional[int] = None
    camera1_id: Optional[int] = None
    camera2_id: Optional[int] = None
    camera3_id: Optional[int] = None

class TeleopGroupInDB(TeleopGroupBase):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    is_active: bool

    class Config:
        from_attributes = True

class TeleopGroupResponse(TeleopGroupBase):
    id: str
    name: str
    description: Optional[str] = None
    running: bool

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    message: str

class TeleopGroupStatusResponse(BaseModel):
    running: bool
    capture_state: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用启动时初始化
    init_tables(DB_PATH)
    print("FastAPI应用启动")
    yield
    # 应用关闭时的清理代码可以放在这里
    print("FastAPI应用正在关闭...")

app = FastAPI(lifespan=lifespan)

def create_device_from_config(device_config):
    """
    根据设备配置创建设备实例
    :param device_config: 设备配置字典
    :return: 设备实例或None
    """
    try:
        device_type = device_config['type']
        device_category = device_config['category']
        config = device_config['config']
        
        # Create device instance based on type and config
        if device_category in DEVICE_CLASSES and device_type in DEVICE_CLASSES[device_category]:
            device_class = DEVICE_CLASSES[device_category][device_type]
            device_instance = device_class(config)
            return device_instance
    except Exception as e:
        print(f"Error creating device instance: config={device_config}, error={e}")
    
    return None

def create_device_from_db(device_id):
    """
    根据数据库中的设备记录创建设备实例
    :param device_id: 设备ID
    :return: 设备实例或None
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT type, category, config FROM devices WHERE id=?", (device_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    type_, category, config_str = row
    try:
        config = json.loads(config_str)
        # Create device instance based on type and config
        device_config = {
            "type": type_,
            "category": category,
            "config": config
        }
        device_instance = create_device_from_config(device_config)
        if device_instance:
            # 设置设备ID用于状态更新
            device_instance.id = device_id
            return device_instance
    except Exception as e:
        print(f"Error creating device instance: id={device_id}, type={type_}, error={e}")
    
    return None

def create_teleop_group_instance(group_type, config):
    """
    根据类型和配置创建遥操组实例
    :param group_type: 遥操组类型
    :param config: 配置信息，包含设备实例列表
    :return: 遥操组实例
    """
    try:
        # 创建设备实例
        device_instances = {}
        for device_config in config:
            device_id = device_config['id']
            device_instance = create_device_from_db(device_id)
            if device_instance:
                device_instances[device_id] = device_instance
        
        # 创建遥操组实例
        if group_type in TELEOP_GROUP_CLASSES:
            teleop_group_class = TELEOP_GROUP_CLASSES[group_type]
            teleop_group = teleop_group_class(config)
            teleop_group.devices = device_instances
            return teleop_group
        else:
            # 默认使用默认类型
            from TeleopGroup.DefaultTeleopGroup import DefaultTeleopGroup
            teleop_group = DefaultTeleopGroup(config)
            teleop_group.devices = device_instances
            return teleop_group
    except Exception as e:
        print(f"创建遥操组实例失败: {e}")
        return None

# 1. 获取所有设备
@app.get("/api/devices", response_model=List[Device])
def get_all_devices(category: Optional[str] = None):
    conn = get_db_conn()
    cursor = conn.cursor()
    
    if category:
        cursor.execute("SELECT id, name, description, category, type, config FROM devices WHERE category=?", (category,))
    else:
        cursor.execute("SELECT id, name, description, category, type, config FROM devices")
        
    rows = cursor.fetchall()
    conn.close()
    
    devices = []
    for row in rows:
        device = Device(
            id=row[0],
            name=row[1],
            description=row[2],
            category=row[3],
            type=row[4],
            config=json.loads(row[5]) if row[5] else {}
        )
        devices.append(device)
    
    return devices


# 获取适配类型及config字段
@app.get("/api/device/types", response_model=DeviceTypeConfigResponse)
def get_device_types_api(category: str):
    if category not in DEVICE_TYPES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备类别不存在")
    
    return DEVICE_TYPES[category]

# 获取所有设备分类
@app.get("/api/device/categories", response_model=DeviceCategoryResponse)
def get_device_categories():
    return DeviceCategoryResponse(categories=list(DEVICE_CONFIG.keys()))


# 新增设备（卡片添加）
@app.post("/api/devices", status_code=status.HTTP_201_CREATED, response_model=DeviceCreateResponse)
def add_device(device: DeviceCreate):
    type_ = device.type
    config = device.config
    name = device.name
    describe = device.describe
    category = device.category
    
    # 只允许选择已适配类型
    if category not in DEVICE_CLASSES or type_ not in DEVICE_CLASSES[category]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"类型 {type_} 未适配于 {category}")
    # 检查config字段
    device_class = DEVICE_CLASSES[category][type_]
    # 使用类方法获取所需配置字段
    if hasattr(device_class, 'get_need_config'):
        required_fields = device_class.get_need_config()
        # 只获取字段名列表
        if isinstance(required_fields, dict):
            required_fields = list(required_fields.keys())
    else:
        required_fields = []
        
    for field in required_fields:
        if field not in config:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"缺少配置字段: {field}")
    
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO devices (name, description, category, type, config) VALUES (?, ?, ?, ?, ?)", (name, describe, category, type_, json.dumps(config)))
    device_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return DeviceCreateResponse(message="设备已添加", id=device_id)

# 获取设备详情
@app.get("/api/devices/{device_id}", response_model=Device)
def get_device_by_id(device_id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, category, type, config FROM devices WHERE id=?", (device_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在")
    
    device = Device(
        id=row[0],
        name=row[1],
        description=row[2],
        category=row[3],
        type=row[4],
        config=json.loads(row[5]) if row[5] else {}
    )
    
    return device

# 2. 修改某个设备 config
@app.put("/api/devices/{id}", response_model=MessageResponse)
def update_device_config(id: int, device_update: DeviceUpdate):
    config = device_update.config
    category = device_update.category
    # 获取设备类型
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT type, category FROM devices WHERE id=?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在")
    type_ = row[0]
    orig_category = row[1]
    
    # 如果提供了新的category，则使用新的，否则使用原来的
    device_category = category if category else orig_category
    
    # 只允许选择已适配类型
    if device_category not in DEVICE_CLASSES or type_ not in DEVICE_CLASSES[device_category]:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"类型 {type_} 未适配于 {device_category}")
    # 检查config字段
    device_class = DEVICE_CLASSES[device_category][type_]
    # 使用类方法获取所需配置字段
    if hasattr(device_class, 'get_need_config'):
        required_fields = device_class.get_need_config()
    else:
        required_fields = {}
        
    for field in required_fields:
        if field not in config:
            conn.close()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"缺少配置字段: {field}")
    cursor.execute("UPDATE devices SET config=?, category=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (json.dumps(config), device_category, id))
    conn.commit()
    conn.close()
    return MessageResponse(message="配置已更新")



# 5. 删除设备（彻底从数据库移除）
@app.delete("/api/devices/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM devices WHERE id=?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在")
    cursor.execute("DELETE FROM devices WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return None

# 获取设备连接状态
@app.get("/api/devices/{id}/status", response_model=DeviceStatusResponse)
def get_device_conn_status(id: int):
    # 从数据库获取设备状态
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM devices WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在")
    
    status = row[0] if row[0] is not None else 0
    print(f"[ConnStatus] id={id}, status={status}")
    return DeviceStatusResponse(conn_status=status)


# 获取所有遥操组类型配置
@app.get("/api/teleop-group/types", response_model=Dict[str, Any])
def get_teleop_group_types_api():
    return TELEOP_GROUP_TYPES

# 获取所有遥操作组
@app.get("/api/teleop-groups", response_model=List[TeleopGroupResponse])
def get_all_teleop_groups(vr_id: Optional[int] = None, name: Optional[str] = None):
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # 构建查询语句
    query = "SELECT id, name, describe, type, config, created_at, updated_at FROM teleop_groups WHERE 1=1"
    params = []
    
    if vr_id is not None:
        query += " AND vr_id=?"
        params.append(vr_id)
    
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    groups = []
    for row in rows:
        # 解析配置
        try:
            config = json.loads(row[4]) if row[4] else {}
        except:
            config = {}
            
        group = TeleopGroupResponse(
            id=str(row[0]),
            name=row[1],
            describe=row[2],
            running=str(row[0]) in TELEOP_GROUPS and TELEOP_GROUPS[str(row[0])].running,
            **config
        )
        groups.append(group)
    
    return groups

# 创建遥操作组
@app.post("/api/teleop-groups", status_code=status.HTTP_201_CREATED, response_model=TeleopGroupCreateResponse)
def create_teleop_group(teleop_group: TeleopGroupCreate):
    # 插入新记录
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO teleop_groups 
                     (name, description, left_arm_id, right_arm_id, vr_id, camera1_id, camera2_id, camera3_id) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (teleop_group.name, teleop_group.description,
                   teleop_group.left_arm_id, teleop_group.right_arm_id, teleop_group.vr_id,
                   teleop_group.camera1_id, teleop_group.camera2_id, teleop_group.camera3_id))
    
    # 获取数据库生成的自增ID
    new_group_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # 在内存中创建对象
    config = {
        "left_arm_id": teleop_group.left_arm_id,
        "right_arm_id": teleop_group.right_arm_id,
        "vr_id": teleop_group.vr_id,
        "camera1_id": teleop_group.camera1_id,
        "camera2_id": teleop_group.camera2_id,
        "camera3_id": teleop_group.camera3_id
    }
    TELEOP_GROUPS[new_group_id] = TeleopGroup(new_group_id, config)
    
    return TeleopGroupCreateResponse(message="遥操作组已创建", id=str(new_group_id))

# 更新遥操作组
@app.put("/api/teleop-groups/{group_id}", response_model=MessageResponse)
def update_teleop_group(group_id: str, teleop_group: TeleopGroupUpdate):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM teleop_groups WHERE id=?", (group_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    
    # 更新记录
    cursor.execute('''UPDATE teleop_groups SET 
                     name=COALESCE(?, name), 
                     description=COALESCE(?, description),
                     left_arm_id=COALESCE(?, left_arm_id),
                     right_arm_id=COALESCE(?, right_arm_id),
                     vr_id=COALESCE(?, vr_id),
                     camera1_id=COALESCE(?, camera1_id),
                     camera2_id=COALESCE(?, camera2_id),
                     camera3_id=COALESCE(?, camera3_id),
                     updated_at=CURRENT_TIMESTAMP
                     WHERE id=?''',
                  (teleop_group.name, teleop_group.description,
                   teleop_group.left_arm_id, teleop_group.right_arm_id, teleop_group.vr_id,
                   teleop_group.camera1_id, teleop_group.camera2_id, teleop_group.camera3_id,
                   group_id))
    conn.commit()
    conn.close()
    
    # 更新内存中的对象
    if group_id in TELEOP_GROUPS:
        config = {
            "left_arm_id": teleop_group.left_arm_id or TELEOP_GROUPS[group_id].config.get("left_arm_id"),
            "right_arm_id": teleop_group.right_arm_id or TELEOP_GROUPS[group_id].config.get("right_arm_id"),
            "vr_id": teleop_group.vr_id or TELEOP_GROUPS[group_id].config.get("vr_id"),
            "camera1_id": teleop_group.camera1_id or TELEOP_GROUPS[group_id].config.get("camera1_id"),
            "camera2_id": teleop_group.camera2_id or TELEOP_GROUPS[group_id].config.get("camera2_id"),
            "camera3_id": teleop_group.camera3_id or TELEOP_GROUPS[group_id].config.get("camera3_id")
        }
        TELEOP_GROUPS[group_id].config = config
    else:
        # 如果内存中没有对象，则创建
        config = {
            "left_arm_id": teleop_group.left_arm_id,
            "right_arm_id": teleop_group.right_arm_id,
            "vr_id": teleop_group.vr_id,
            "camera1_id": teleop_group.camera1_id,
            "camera2_id": teleop_group.camera2_id,
            "camera3_id": teleop_group.camera3_id
        }
        TELEOP_GROUPS[group_id] = TeleopGroup(group_id, config)
    
    return MessageResponse(message="遥操作组已更新")

# 删除遥操作组
@app.delete("/api/teleop-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teleop_group(group_id: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM teleop_groups WHERE id=?", (group_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    
    # 删除记录
    cursor.execute("DELETE FROM teleop_groups WHERE id=?", (group_id,))
    conn.commit()
    conn.close()
    
    # 从内存中移除对象
    if group_id in TELEOP_GROUPS:
        del TELEOP_GROUPS[group_id]
    
    return None

# 获取遥操作组配置
@app.get("/api/teleop-groups/{group_id}", response_model=TeleopGroupResponse)
def get_teleop_group_by_id(group_id: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, type, config, created_at, updated_at FROM teleop_groups WHERE id=?", (group_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    
    # 解析配置
    try:
        config = json.loads(row[4]) if row[4] else []
    except:
        config = []
        
    group = TeleopGroupResponse(
        id=str(row[0]),
        name=row[1],
        description=row[2],
        type=row[3],
        config=config,
        created_at=row[5],
        updated_at=row[6],
        running=str(row[0]) in TELEOP_GROUPS and TELEOP_GROUPS[str(row[0])].running
    )
    
    return group

# 启动遥操作组
@app.post("/api/teleop-groups/{group_id}/start", response_model=MessageResponse)
# about bussiness logic
def start_teleop_group(group_id: str):
    # 如果内存中已经存在对象且正在运行，则直接返回
    if group_id in TELEOP_GROUPS and TELEOP_GROUPS[group_id].running:
        return MessageResponse(message="遥操作已在运行")
    
    # 检查是否存在
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, config FROM teleop_groups WHERE id=?", (group_id,))
    group_row = cursor.fetchone()
    if not group_row:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在或未启用")
    
    group_type = group_row[1] if group_row[1] else "DefaultTeleopGroup"
    config_str = group_row[2]
    
    try:
        config = json.loads(config_str) if config_str else []
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"解析遥操组配置失败: {e}")
    
    conn.close()
    
    # 如果内存中没有对象或对象未运行，则创建新实例
    if group_id not in TELEOP_GROUPS or not TELEOP_GROUPS[group_id].running:
        TELEOP_GROUPS[group_id] = create_teleop_group_instance(group_type, config)
    
    # 启动遥操作组
    if TELEOP_GROUPS[group_id]:
        success = TELEOP_GROUPS[group_id].start()
        if success:
            return MessageResponse(message="遥操作已启动")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="遥操作组启动失败")
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="遥操作组实例创建失败")

# 停止遥操作组
@app.post("/api/teleop-groups/{group_id}/stop", response_model=MessageResponse)
def stop_teleop_group(group_id: str):
    if group_id not in TELEOP_GROUPS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    
    success = TELEOP_GROUPS[group_id].stop()
    if success:
        return MessageResponse(message="遥操作已停止")
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="遥操作组停止失败")

# 获取遥操作组状态
@app.get("/api/teleop-groups/{group_id}/status", response_model=TeleopGroupStatusResponse)
def get_teleop_group_status(group_id: str):
    group = TELEOP_GROUPS.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    
    capture_state = group.data_collect.get_capture_state() if group.data_collect else 0
    
    return TeleopGroupStatusResponse(
        running=group.running,
        capture_state=capture_state
    )

@app.get("/", response_class=RedirectResponse)
async def root_redirect():
    return "/index.html"

app.mount("/", StaticFiles(directory="static"), name="index")

if __name__ == "__main__":
    # 配置Uvicorn参数
    uvicorn.run(
        app="server:app",  # 指明FastAPI应用的位置（模块名:应用实例名）
        host="0.0.0.0",  # 允许外部访问
        port=8000,       # 端口号
        reload=False,     # 开发模式下启用自动重载（生产环境建议关闭）
        workers=1        # 工作进程数（单进程即可，多进程可能影响WebSocket）
    )