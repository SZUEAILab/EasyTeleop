import yaml
from fastapi import FastAPI, HTTPException, Body, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Union
import threading
import uvicorn  # 导入uvicorn
import sqlite3
import os
import json
from contextlib import asynccontextmanager

from Device.Camera.RealSenseCamera import RealSenseCamera
from Device.Robot.RealMan import RM_controller
from Device.VR.VRSocket import VRSocket

from TeleopMiddleware import TeleopMiddleware
from DataCollect import DataCollect

# 遥操作组管理
TELEOP_GROUPS = {}

# 全局设备池变量
# 注意：这个变量需要在FastAPI应用启动时初始化，而不是在if __name__ == "__main__"中初始化
# 原因如下：
# 1. 当使用uvicorn.run()运行FastAPI应用时，实际会启动一个独立的服务器进程
# 2. 在这个进程中，只有被导入的模块会被执行，而if __name__ == "__main__"块中的代码不会被执行
# 3. lifespan事件处理器确保在FastAPI应用实际启动并准备处理请求之前执行初始化代码
# 4. 这样可以确保在所有API路由中都能访问到正确初始化的device_pool
device_pool = {}


def parse_device_id(device_id):
    """Helper function to parse device ID from config"""
    if device_id is None:
        return None
    if isinstance(device_id, str) and device_id.isdigit():
        return int(device_id)
    return device_id if isinstance(device_id, int) else None


class TeleopGroup:
    def __init__(self, group_id, config):
        self.id = group_id
        self.config = config
        self.teleop = TeleopMiddleware()
        self.data_collect = DataCollect()
        self.running = False
        # 设备引用
        self.left_arm = None
        self.right_arm = None
        self.vr = None
        self.camera1 = None
        self.camera2 = None
        self.camera3 = None

    def start(self, device_pool):
        print("TeleopGroup.start中设备池内容:", list(device_pool.keys()))
        # 启动数据采集
        self.data_collect.start()
        self.teleop.on("buttonATurnDown", self.data_collect.toggle_capture_state)
        # 按照配置引用device_pool中配置的设备
        print(self.config)
        # 左手臂
        left_id = parse_device_id(self.config.get('left_arm_id'))
        self.left_arm = device_pool.get(left_id) if left_id else None
        if self.left_arm:
            self.teleop.on("leftGripDown", self.left_arm.start_control)
            self.teleop.on("leftGripUp", self.left_arm.stop_control)
            # 注册数据采集回调
            self.left_arm.on("state", self.data_collect.put_robot_state)
        # 右手臂
        right_id = parse_device_id(self.config.get('right_arm_id'))
        self.right_arm = device_pool.get(right_id) if right_id else None
        if self.right_arm:
            self.teleop.on("rightGripDown", self.right_arm.start_control)
            self.teleop.on("rightGripUp", self.right_arm.stop_control)
            # 注册数据采集回调
            self.right_arm.on("state", self.data_collect.put_robot_state)
        # VR头显
        vr_id = parse_device_id(self.config.get('vr_id'))
        self.vr = device_pool.get(vr_id) if vr_id else None
        if self.vr:
            self.vr.on("message",self.teleop.handle_socket_data)
        # 摄像头（可选）
        camera1_id = parse_device_id(self.config.get('camera1_id'))
        self.camera1 = device_pool.get(camera1_id) if camera1_id else None
        if self.camera1:
            # 注册数据采集回调
            self.camera1.on("frame", self.data_collect.put_video_frame)
        
        camera2_id = parse_device_id(self.config.get('camera2_id'))
        self.camera2 = device_pool.get(camera2_id) if camera2_id else None
        if self.camera2:
            # 注册数据采集回调
            self.camera2.on("frame", self.data_collect.put_video_frame)
        
        camera3_id = parse_device_id(self.config.get('camera3_id'))
        self.camera3 = device_pool.get(camera3_id) if camera3_id else None
        if self.camera3:
            # 注册数据采集回调
            self.camera3.on("frame", self.data_collect.put_video_frame)
        
        self.running = True

    def stop(self):
        # 停止数据采集
        self.data_collect.stop()
        # 仅停止teleop逻辑，不操作设备
        if self.vr:
            self.vr.off("message")
        if self.left_arm:
            self.teleop.off("leftGripDown")
            self.teleop.off("leftGripUp")
            self.left_arm.off("state")
        if self.right_arm:
            self.teleop.off("rightGripDown")
            self.teleop.off("rightGripUp")
            self.right_arm.off("state")
        if self.camera1:
            self.camera1.off("frame")
        if self.camera2:
            self.camera2.off("frame")
        if self.camera3:
            self.camera3.off("frame")
        self.running = False



def init_device_tables(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # 设备表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(20) NOT NULL,
            describe TEXT NOT NULL,
            category VARCHAR(20) NOT NULL,
            type VARCHAR(20) NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # 遥操作组表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teleop_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            describe TEXT,
            left_arm_id INTEGER,
            right_arm_id INTEGER,
            vr_id INTEGER,
            camera1_id INTEGER,
            camera2_id INTEGER,
            camera3_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (left_arm_id) REFERENCES devices (id),
            FOREIGN KEY (right_arm_id) REFERENCES devices (id),
            FOREIGN KEY (vr_id) REFERENCES devices (id),
            FOREIGN KEY (camera1_id) REFERENCES devices (id),
            FOREIGN KEY (camera2_id) REFERENCES devices (id),
            FOREIGN KEY (camera3_id) REFERENCES devices (id)
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
    describe: str
    category: str
    type: str
    config: dict

class DeviceCreate(DeviceBase):
    category: str
    pass

class DeviceCreateResponse(BaseModel):
    message: str
    id: int

class DeviceUpdate(BaseModel):
    config: dict
    category: Optional[str] = None

class Device(DeviceBase):
    id: int
    category: str

    class Config:
        from_attributes = True

class DeviceStatusResponse(BaseModel):
    conn_status: int

class DeviceCategoryResponse(BaseModel):
    categories: List[str]

class DeviceTypeConfigResponse(BaseModel):
    __root__: Dict[str, List[str]]
    
    class Config:
        schema_extra = {
            "example": {
                "RealMan": ["ip", "port"],
                "Quest": ["ip", "port"],
                "RealSense": ["camera_type", "camera_position", "camera_serial"]
            }
        }

class TeleopGroupBase(BaseModel):
    name: str
    describe: Optional[str] = None
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
    describe: Optional[str] = None
    left_arm_id: Optional[int] = None
    right_arm_id: Optional[int] = None
    vr_id: Optional[int] = None
    camera1_id: Optional[int] = None
    camera2_id: Optional[int] = None
    camera3_id: Optional[int] = None

class TeleopGroupInDB(TeleopGroupBase):
    id: str
    name: str
    describe: Optional[str] = None
    created_at: str
    updated_at: str
    is_active: bool

    class Config:
        from_attributes = True

class TeleopGroupResponse(TeleopGroupBase):
    id: str
    name: str
    describe: Optional[str] = None
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
    # 在应用启动时初始化设备池
    init_device_tables(DB_PATH)
    init_device_pool()
    init_teleop_groups()
    print("FastAPI应用启动，设备池内容:", list(device_pool.keys()))
    print("FastAPI应用启动，遥操作组内容:", list(TELEOP_GROUPS.keys()))
    yield
    # 应用关闭时的清理代码可以放在这里
    print("FastAPI应用正在关闭...")

app = FastAPI(lifespan=lifespan)

DB_PATH = "teleop_data.db"

# 
DEVICE_CONFIG = {
    "vr": {
        "Quest": VRSocket
        },        
    "robot": {
        "RealMan": RM_controller
        },       
    "camera": {
        "RealSense": RealSenseCamera,
        }     
}

# Initialize device pool based on database records
def init_device_pool():
    global device_pool
    device_pool = {}  # Flat structure with unique IDs as keys
    
    conn = get_db_conn()
    cursor = conn.cursor()
    
    for category in DEVICE_CONFIG:
        cursor.execute("SELECT id, type, config FROM devices WHERE category=? AND is_active=1", (category,))
        rows = cursor.fetchall()
        for row in rows:
            id, type_, config_str = row
            try:
                config = json.loads(config_str)
                # Create device instance based on type and config
                if type_ in DEVICE_CONFIG[category]:
                    device_class = DEVICE_CONFIG[category][type_]
                    device_instance = device_class(config)
                    # Store device instance with ID as direct key
                    device_pool[id] = device_instance
            except Exception as e:
                print(f"Error creating device instance: id={id}, type={type_}, error={e}")
    
    conn.close()

# Initialize teleop groups based on database records
def init_teleop_groups():
    global TELEOP_GROUPS
    TELEOP_GROUPS = {}
    
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, left_arm_id, right_arm_id, vr_id, camera1_id, camera2_id, camera3_id FROM teleop_groups WHERE is_active=1")
    rows = cursor.fetchall()
    conn.close()
    
    for row in rows:
        group_id = row[0]
        config = {
            "left_arm_id": row[1],
            "right_arm_id": row[2],
            "vr_id": row[3],
            "camera1_id": row[4],
            "camera2_id": row[5],
            "camera3_id": row[6]
        }
        TELEOP_GROUPS[group_id] = TeleopGroup(group_id, config)

# 1. 获取所有设备 type+config
@app.get("/api/devices", response_model=List[Device])
def get_all_devices(category: Optional[str] = None):
    conn = get_db_conn()
    cursor = conn.cursor()
    result = []
    
    # 如果提供了category参数，则只查询该类别的设备
    if category:
        cursor.execute("SELECT id,name,describe,category,type,config FROM devices WHERE category=?", (category,))
        rows = cursor.fetchall()
        for r in rows:
            result.append({"id": r[0], "name": r[1], "describe": r[2], "category": r[3], "type": r[4], "config": json.loads(r[5])})
    else:
        # 否则查询所有设备
        cursor.execute("SELECT id,name,describe,category,type,config FROM devices")
        rows = cursor.fetchall()
        for r in rows:
            result.append({"id": r[0], "name": r[1], "describe": r[2], "category": r[3], "type": r[4], "config": json.loads(r[5])})
            
    conn.close()
    return result


# 获取适配类型及config字段
@app.get("/api/device/types", response_model=DeviceTypeConfigResponse)
def get_adapted_types(category: str):
    if category not in DEVICE_CONFIG:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="类别错误")
    result = {}
    for key, cls in DEVICE_CONFIG[category].items():
        # 确保是类且具有 get_need_config 方法
        if not hasattr(cls, 'get_need_config'):
            result[key] = []
            continue
        try:
            config_fields = cls.get_need_config()
            # 只返回字段名列表，而不是字段名和描述
            result[key] = list(config_fields.keys()) if isinstance(config_fields, dict) else config_fields
        except Exception as e:
            print(f"[Error] 获取设备类型 {category}/{key} 的配置字段失败: {e}")
            result[key] = []
    return {"__root__": result}

# 新增设备（卡片添加）
@app.post("/api/devices", status_code=status.HTTP_201_CREATED, response_model=DeviceCreateResponse)
def add_device(device: DeviceCreate):
    type_ = device.type
    config = device.config
    name = device.name
    describe = device.describe
    category = device.category
    
    # 只允许选择已适配类型
    if category not in DEVICE_CONFIG or type_ not in DEVICE_CONFIG[category]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"类型 {type_} 未适配于 {category}")
    # 检查config字段
    device_class = DEVICE_CONFIG[category][type_]
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
    cursor.execute("INSERT INTO devices (name, describe, category, type, config) VALUES (?, ?, ?, ?, ?)", (name, describe, category, type_, json.dumps(config)))
    device_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return DeviceCreateResponse(message="设备已添加", id=device_id)

# 获取单个设备详情
@app.get("/api/devices/{id}", response_model=Device)
def get_device(id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, describe, category, type, config FROM devices WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在")
    return Device(id=row[0], name=row[1], describe=row[2], category=row[3], type=row[4], config=json.loads(row[5]))


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
    if device_category not in DEVICE_CONFIG or type_ not in DEVICE_CONFIG[device_category]:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"类型 {type_} 未适配于 {device_category}")
    # 检查config字段
    device_class = DEVICE_CONFIG[device_category][type_]
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
    # 若对象已启动则同步更新对象 config
    if id in device_pool:
        device = device_pool[id]
        if hasattr(device, 'update_config'):
            device.update_config(config)
    return MessageResponse(message="配置已更新")

# 3. 启动设备对象
@app.post("/api/devices/{id}/start", response_model=MessageResponse)
def start_device(id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT type, category, config FROM devices WHERE id=? AND is_active=1", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在或未启用")
    # 初始化对象,about bussiness logic
    type_, category, config = row[0], row[1], json.loads(row[2])
    
    obj = DEVICE_CONFIG[category][type_](config)
    if obj and hasattr(obj, 'start'):
        obj.start()
    # Store in device_pool with ID as direct key
    device_pool[id] = obj
    return MessageResponse(message="设备已启动")

# 4. 停止并删除设备对象
@app.post("/api/devices/{id}/stop", response_model=MessageResponse)
def stop_device(id: int):
    if id not in device_pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备未启动")
    obj = device_pool[id]
    if hasattr(obj, 'stop'):
        obj.stop()
    del device_pool[id]
    return MessageResponse(message="设备已停止并删除")


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
    # 同时从设备池移除对象（如果有）
    if id in device_pool:
        del device_pool[id]
    return None

# 获取设备连接状态
@app.get("/api/devices/{id}/status", response_model=DeviceStatusResponse)
def get_device_conn_status(id: int):
    if id not in device_pool:
        status = 0  # 未连接
    else:
        device = device_pool[id]
        if hasattr(device, 'get_conn_status'):
            status = device.get_conn_status()
        elif hasattr(device, 'is_connected'):
            # 兼容部分Camera类
            status = 1 if device.is_connected() else 2
        else:
            status = 0
    print(f"[ConnStatus] id={id}, status={status}")
    return DeviceStatusResponse(conn_status=status)


# 获取所有设备分类
@app.get("/api/device/categories", response_model=DeviceCategoryResponse)
def get_device_categories():
    return DeviceCategoryResponse(categories=list(DEVICE_CONFIG.keys()))

# 获取所有遥操作组列表
@app.get("/api/teleop-groups", response_model=List[TeleopGroupInDB])
def list_teleop_groups(vr_id: Optional[int] = None, name: Optional[str] = None):
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # 构建查询语句
    query = "SELECT id, name, describe, left_arm_id, right_arm_id, vr_id, camera1_id, camera2_id, camera3_id, created_at, updated_at, is_active FROM teleop_groups WHERE is_active=1"
    params = []
    
    # 添加查询条件
    if vr_id is not None:
        query += " AND vr_id=?"
        params.append(vr_id)
        
    if name is not None:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append(TeleopGroupInDB(
            id=row[0],
            name=row[1],
            describe=row[2],
            left_arm_id=row[3],
            right_arm_id=row[4],
            vr_id=row[5],
            camera1_id=row[6],
            camera2_id=row[7],
            camera3_id=row[8],
            created_at=row[9],
            updated_at=row[10],
            is_active=bool(row[11])
        ))
    
    return result

# 创建遥操作组
@app.post("/api/teleop-groups", status_code=status.HTTP_201_CREATED, response_model=TeleopGroupCreateResponse)
def create_teleop_group(teleop_group: TeleopGroupCreate):
    # 插入新记录
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO teleop_groups 
                     (name, describe, left_arm_id, right_arm_id, vr_id, camera1_id, camera2_id, camera3_id) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (teleop_group.name, teleop_group.describe,
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
                     describe=COALESCE(?, describe),
                     left_arm_id=COALESCE(?, left_arm_id),
                     right_arm_id=COALESCE(?, right_arm_id),
                     vr_id=COALESCE(?, vr_id),
                     camera1_id=COALESCE(?, camera1_id),
                     camera2_id=COALESCE(?, camera2_id),
                     camera3_id=COALESCE(?, camera3_id),
                     updated_at=CURRENT_TIMESTAMP
                     WHERE id=?''',
                  (teleop_group.name, teleop_group.describe,
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
@app.get("/api/teleop-groups/{group_id}", response_model=TeleopGroupInDB)
def get_teleop_group(group_id: str):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('''SELECT id, name, describe, left_arm_id, right_arm_id, vr_id, 
                     camera1_id, camera2_id, camera3_id, created_at, updated_at, is_active 
                     FROM teleop_groups WHERE id=?''', (group_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    
    return TeleopGroupInDB(
        id=row[0],
        name=row[1],
        describe=row[2],
        left_arm_id=row[3],
        right_arm_id=row[4],
        vr_id=row[5],
        camera1_id=row[6],
        camera2_id=row[7],
        camera3_id=row[8],
        created_at=row[9],
        updated_at=row[10],
        is_active=bool(row[11])
    )

# 启动遥操作组
@app.post("/api/teleop-groups/{group_id}/start", response_model=MessageResponse)
# about bussiness logic
def start_teleop_group(group_id: str):
    # 检查是否存在
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM teleop_groups WHERE id=? AND is_active=1", (group_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在或未启用")
    
    # 获取配置
    cursor.execute('''SELECT left_arm_id, right_arm_id, vr_id, camera1_id, camera2_id, camera3_id 
                     FROM teleop_groups WHERE id=?''', (group_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组配置不存在")
    
    # 创建配置字典
    config = {
        "left_arm_id": row[0],
        "right_arm_id": row[1],
        "vr_id": row[2],
        "camera1_id": row[3],
        "camera2_id": row[4],
        "camera3_id": row[5]
    }
    
    # 如果内存中没有对象，则创建
    if group_id not in TELEOP_GROUPS:
        TELEOP_GROUPS[group_id] = TeleopGroup(group_id, config)
    else:
        # 更新配置
        TELEOP_GROUPS[group_id].config = config
    
    # 启动遥操作组
    TELEOP_GROUPS[group_id].start(device_pool)
    return MessageResponse(message="遥操作已启动")

# 停止遥操作组
@app.post("/api/teleop-groups/{group_id}/stop", response_model=MessageResponse)
def stop_teleop_group(group_id: str):
    group = TELEOP_GROUPS.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    group.stop()
    return MessageResponse(message="遥操作已停止")


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