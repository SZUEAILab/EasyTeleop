import yaml
from fastapi import FastAPI, HTTPException, Body, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict
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


class TeleopGroup:
    def __init__(self, group_id, config):
        self.id = group_id
        self.config = config
        self.teleop = None
        self.running = False
        # 设备引用
        self.left_arm = None
        self.right_arm = None
        self.vr = None
        self.camera1 = None
        self.camera2 = None
        self.camera3 = None

    def start(self, device_pool):
        print("TeleopGroup.start中设备池内容:", {k: list(v.keys()) for k, v in device_pool.items()})
        # 按照配置引用device_pool
        self.teleop = TeleopMiddleware()
        print(self.config)
        # 左手臂
        left_id = self.config.get('left_arm_id')
        if isinstance(left_id, str) and left_id.isdigit():
            left_id = int(left_id)
        self.left_arm = device_pool['robot'].get(left_id) if left_id else None
        if self.left_arm:
            self.teleop.on("leftGripDown", self.left_arm.start_control)
            self.teleop.on("leftGripUp", self.left_arm.stop_control)
        # 右手臂
        right_id = self.config.get('right_arm_id')
        if isinstance(right_id, str) and right_id.isdigit():
            right_id = int(right_id)
        self.right_arm = device_pool['robot'].get(right_id) if right_id else None
        if self.right_arm:
            self.teleop.on("rightGripDown", self.right_arm.start_control)
            self.teleop.on("rightGripUp", self.right_arm.stop_control)
        # VR头显
        vr_id = self.config.get('vr_id')
        if isinstance(vr_id, str) and vr_id.isdigit():
            vr_id = int(vr_id)
        self.vr = device_pool['vr'].get(vr_id) if vr_id else None
        if self.vr:
            self.vr.on("message",self.teleop.handle_socket_data)
        # 摄像头（可选）
        camera1_id = self.config.get('camera1_id')
        if isinstance(camera1_id, str) and camera1_id.isdigit():
            camera1_id = int(camera1_id)
        self.camera1 = device_pool['camera'].get(camera1_id) if camera1_id else None
        
        camera2_id = self.config.get('camera2_id')
        if isinstance(camera2_id, str) and camera2_id.isdigit():
            camera2_id = int(camera2_id)
        self.camera2 = device_pool['camera'].get(camera2_id) if camera2_id else None
        
        camera3_id = self.config.get('camera3_id')
        if isinstance(camera3_id, str) and camera3_id.isdigit():
            camera3_id = int(camera3_id)
        self.camera3 = device_pool['camera'].get(camera3_id) if camera3_id else None
        
        self.running = True

    def stop(self):
        # 仅停止teleop逻辑，不操作设备
        if self.vr:
            self.vr.off("message")
        if self.left_arm:
            self.teleop.off("leftGripDown")
            self.teleop.off("leftGripUp")
        if self.right_arm:
            self.teleop.off("rightGripDown")
            self.teleop.off("rightGripUp")
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
            id VARCHAR(50) PRIMARY KEY,
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
    type: str
    config: dict

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    config: dict

class Device(DeviceBase):
    id: int

    class Config:
        from_attributes = True

class DeviceStatusResponse(BaseModel):
    conn_status: int

class DeviceCategoryResponse(BaseModel):
    categories: List[str]

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

class TeleopGroupUpdate(TeleopGroupBase):
    name: Optional[str] = None

class TeleopGroupInDB(TeleopGroupBase):
    id: str
    created_at: str
    updated_at: str
    is_active: bool

    class Config:
        from_attributes = True

class TeleopGroupResponse(TeleopGroupBase):
    id: str
    running: bool

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用启动时初始化设备池
    init_device_tables(DB_PATH)
    init_device_pool()
    init_teleop_groups()
    print("FastAPI应用启动，设备池内容:", {k: list(v.keys()) for k, v in device_pool.items()})
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
    device_pool = {category: {} for category in DEVICE_CONFIG}
    
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
                    device_pool[category][id] = device_instance
            except Exception as e:
                print(f"Failed to initialize device {id} of type {type_}: {e}")
    
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
@app.get("/api/devices", response_model=Dict[str, List[Device]])
def get_all_devices():
    conn = get_db_conn()
    cursor = conn.cursor()
    result = {}
    for key in DEVICE_CONFIG:
        cursor.execute(f"SELECT id,name,describe, type, config FROM devices WHERE category=?", (key,))
        rows = cursor.fetchall()
        for r in rows:
            if key not in result:
                result[key] = []
            result[key].append({"id": r[0],"name":r[1],"describe":r[2], "type": r[3], "config": json.loads(r[4])})
    conn.close()
    return result

@app.get("/api/devices/{category}", response_model=List[Device])
def get_all_devices_category(category:str):
    conn = get_db_conn()
    cursor = conn.cursor()
    result = []
    cursor.execute("SELECT id,name,describe, type, config FROM devices WHERE category=?", (category,))
    rows = cursor.fetchall()
    for r in rows:
        result.append({"id": r[0],"name":r[1],"describe":r[2], "type": r[3], "config": json.loads(r[4])})
    conn.close()
    return result


# 获取适配类型及config字段
@app.get("/api/device-types/{category}")
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
            result[key] = config_fields
        except Exception as e:
            print(f"[Error] 获取设备类型 {category}/{key} 的配置字段失败: {e}")
            result[key] = []
    return result

# 新增设备（卡片添加）
@app.post("/api/devices/{category}", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
def add_device(category: str, device: DeviceCreate):
    type_ = device.type
    config = device.config
    name = device.name
    describe = device.describe
    # 只允许选择已适配类型
    if category not in DEVICE_CONFIG or type_ not in DEVICE_CONFIG[category]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"类型 {type_} 未适配于 {category}")
    # 检查config字段
    device_class = DEVICE_CONFIG[category][type_]
    # 使用类方法获取所需配置字段
    if hasattr(device_class, 'get_need_config'):
        required_fields = device_class.get_need_config()
    else:
        required_fields = {}
        
    for field in required_fields:
        if field not in config:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"缺少配置字段: {field}")
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO devices (name, describe, category, type, config) VALUES (?, ?, ?, ?, ?)", (name, describe, category, type_, json.dumps(config)))
    conn.commit()
    conn.close()
    return MessageResponse(message="设备已添加")

# 获取单个设备详情
@app.get("/api/devices/{category}/{id}", response_model=Device)
def get_device(category: str, id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, describe, type, config FROM devices WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在")
    return Device(id=row[0], name=row[1], describe=row[2], type=row[3], config=json.loads(row[4]))


# 2. 修改某个设备 config
@app.put("/api/devices/{category}/{id}", response_model=MessageResponse)
def update_device_config(category: str, id: int, device_update: DeviceUpdate):
    config = device_update.config
    # 获取设备类型
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT type FROM devices WHERE id=?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在")
    type_ = row[0]
    # 只允许选择已适配类型
    if category not in DEVICE_CONFIG or type_ not in DEVICE_CONFIG[category]:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"类型 {type_} 未适配于 {category}")
    # 检查config字段
    device_class = DEVICE_CONFIG[category][type_]
    # 使用类方法获取所需配置字段
    if hasattr(device_class, 'get_need_config'):
        required_fields = device_class.get_need_config()
    else:
        required_fields = {}
        
    for field in required_fields:
        if field not in config:
            conn.close()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"缺少配置字段: {field}")
    cursor.execute("UPDATE devices SET config=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (json.dumps(config), id))
    conn.commit()
    conn.close()
    # 若对象已启动则同步更新对象 config
    if id in device_pool.get(category, {}):
        device = device_pool[category][id]
        if hasattr(device, 'update_config'):
            device.update_config(config)
    return MessageResponse(message="配置已更新")

# 3. 启动设备对象
@app.post("/api/devices/{category}/{id}/start", response_model=MessageResponse)
def start_device(category: str, id: int):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT type, config FROM devices WHERE id=? AND is_active=1", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在或未启用")
    # 初始化对象,about bussiness logic
    type_, config = row[0], json.loads(row[1])
    
    obj = DEVICE_CONFIG[category][type_](config)
    if obj and hasattr(obj, 'start'):
        obj.start()
    # 确保 category 存在于 device_pool 中
    if category not in device_pool:
        device_pool[category] = {}
    device_pool[category][id] = obj
    return MessageResponse(message="设备已启动")

# 4. 停止并删除设备对象
@app.post("/api/devices/{category}/{id}/stop", response_model=MessageResponse)
def stop_device(category: str, id: int):
    pool = device_pool.get(category, {})
    if id not in pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备未启动")
    obj = pool[id]
    if hasattr(obj, 'stop'):
        obj.stop()
    del pool[id]
    return MessageResponse(message="设备已停止并删除")


# 5. 删除设备（彻底从数据库移除）
@app.delete("/api/devices/{category}/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(category: str, id: int):
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
    if category in device_pool and id in device_pool[category]:
        del device_pool[category][id]
    return None

# 获取设备连接状态
@app.get("/api/devices/{category}/{id}/status", response_model=DeviceStatusResponse)
def get_device_conn_status(category: str, id: int):
    pool = device_pool.get(category, {})
    if id not in pool:
        status = 0  # 未连接
    else:
        device = pool[id]
        if hasattr(device, 'get_conn_status'):
            status = device.get_conn_status()
        elif hasattr(device, 'is_connected'):
            # 兼容部分Camera类
            status = 1 if device.is_connected() else 2
        else:
            status = 0
    print(f"[ConnStatus] category={category}, id={id}, status={status}")
    return DeviceStatusResponse(conn_status=status)


# 获取所有设备分类
@app.get("/api/device-categories", response_model=DeviceCategoryResponse)
def get_device_categories():
    return DeviceCategoryResponse(categories=list(DEVICE_CONFIG.keys()))

# 获取所有遥操作组列表
@app.get("/api/teleop-groups", response_model=List[TeleopGroupResponse])
def list_teleop_groups():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, describe, left_arm_id, right_arm_id, vr_id, camera1_id, camera2_id, camera3_id FROM teleop_groups WHERE is_active=1")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        group_id = row[0]
        config = {
            "left_arm_id": row[3],
            "right_arm_id": row[4],
            "vr_id": row[5],
            "camera1_id": row[6],
            "camera2_id": row[7],
            "camera3_id": row[8]
        }
        # Check if group is running
        running = group_id in TELEOP_GROUPS and TELEOP_GROUPS[group_id].running
        result.append(TeleopGroupResponse(id=group_id, name=row[1], describe=row[2], **config, running=running))
    
    return result

# 创建遥操作组
@app.post("/api/teleop-groups/{group_id}", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
def create_teleop_group(group_id: str, teleop_group: TeleopGroupCreate):
    # 检查是否已存在
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM teleop_groups WHERE id=?", (group_id,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="遥操作组已存在")
    
    # 插入新记录
    cursor.execute('''INSERT INTO teleop_groups 
                     (id, name, describe, left_arm_id, right_arm_id, vr_id, camera1_id, camera2_id, camera3_id) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (group_id, teleop_group.name, teleop_group.describe,
                   teleop_group.left_arm_id, teleop_group.right_arm_id, teleop_group.vr_id,
                   teleop_group.camera1_id, teleop_group.camera2_id, teleop_group.camera3_id))
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
    TELEOP_GROUPS[group_id] = TeleopGroup(group_id, config)
    
    return MessageResponse(message="遥操作组已创建")

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