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

from Device.Camera.RealSenseCamera import RealSenseCamera
from Device.Robot.RealMan import RM_controller
from Device.VR.VRSocket import VRSocket

from TeleopGroup import TeleopGroup

# 遥操作组管理
TELEOP_GROUPS = {}



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
        orm_mode = True

class DeviceStatusResponse(BaseModel):
    conn_status: int

class DeviceCategoryResponse(BaseModel):
    categories: List[str]

class TeleopGroupBase(BaseModel):
    config: dict

class TeleopGroupCreate(TeleopGroupBase):
    pass

class TeleopGroupUpdate(TeleopGroupBase):
    pass

class TeleopGroupResponse(TeleopGroupBase):
    id: str
    running: bool

    class Config:
        orm_mode = True

class MessageResponse(BaseModel):
    message: str

app = FastAPI()

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

device_pool = {}


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
    for key, value in DEVICE_CONFIG[category].items():
        if hasattr(value, 'required_config_fields'):
            result[key] = value.required_config_fields
        else:
            result[key] = []
    return DEVICE_CONFIG[category]

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
    required_fields = DEVICE_CONFIG[category][type_]
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
    required_fields = DEVICE_CONFIG[category][type_]
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
    return [
        TeleopGroupResponse(id=g.id, config=g.config, running=g.running)
        for g in TELEOP_GROUPS.values()
    ]

# 创建遥操作组
@app.post("/api/teleop-groups/{group_id}", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
def create_teleop_group(group_id: str, teleop_group: TeleopGroupCreate):
    if group_id in TELEOP_GROUPS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="遥操作组已存在")
    TELEOP_GROUPS[group_id] = TeleopGroup(group_id, teleop_group.config)
    return MessageResponse(message="遥操作组已创建")

# 更新遥操作组
@app.put("/api/teleop-groups/{group_id}", response_model=MessageResponse)
def update_teleop_group(group_id: str, teleop_group: TeleopGroupUpdate):
    if group_id not in TELEOP_GROUPS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    TELEOP_GROUPS[group_id].config = teleop_group.config
    return MessageResponse(message="遥操作组已更新")

# 删除遥操作组
@app.delete("/api/teleop-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teleop_group(group_id: str):
    if group_id not in TELEOP_GROUPS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    del TELEOP_GROUPS[group_id]
    return None

# 获取遥操作组配置
@app.get("/api/teleop-groups/{group_id}", response_model=TeleopGroupResponse)
def get_teleop_group(group_id: str):
    group = TELEOP_GROUPS.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    return TeleopGroupResponse(id=group.id, config=group.config, running=group.running)

# 启动遥操作组
@app.post("/api/teleop-groups/{group_id}/start", response_model=MessageResponse)
# about bussiness logic
def start_teleop_group(group_id: str):
    group = TELEOP_GROUPS.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="遥操作组不存在")
    group.start()
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
    db_path = os.path.join(os.path.dirname(__file__), "teleop_data.db")
    init_device_tables(db_path)
    # Initialize device pool with existing devices
    init_device_pool()
    # 配置Uvicorn参数
    uvicorn.run(
        app="server:app",  # 指明FastAPI应用的位置（模块名:应用实例名）
        host="0.0.0.0",  # 允许外部访问
        port=8000,       # 端口号
        reload=True,     # 开发模式下启用自动重载（生产环境建议关闭）
        workers=1        # 工作进程数（单进程即可，多进程可能影响WebSocket）
    )