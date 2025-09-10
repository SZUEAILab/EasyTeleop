import yaml
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict
import threading
import uvicorn  # 导入uvicorn
import sqlite3
import os
import json

from Camera.RealSenseCamera import RealSenseCamera
from Robots.RealMan import RM_controller
from VRSocket import VRSocket
from Teleoperation import Teleoperation


def init_device_tables(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # 机械臂表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS robotic_arm (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type VARCHAR(50) NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    
    ''')
    # 摄像头表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS camera (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type VARCHAR(50) NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # VR 头显表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vr_headset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type VARCHAR(50) NOT NULL,
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()


# 辅助：类别转表名
def get_table_name(category):
    if category == "arm":
        return "robotic_arm"
    elif category == "camera":
        return "camera"
    elif category == "vr":
        return "vr_headset"
    else:
        raise HTTPException(400, "类别错误")

# 辅助：根据类别和 type 初始化对象
def create_device_instance(category, type_, config):
    if category == "arm":
        return RM_controller(config)
    elif category == "camera":
        # RealSenseCamera 构造参数兼容 config
        if type_ == "RealSense":
            # 兼容 config 可能为 {"camera_type", "camera_position", "camera_serial"}
            return RealSenseCamera(
                config.get("camera_type", "RealSense"),
                config.get("camera_position", "default"),
                config.get("camera_serial", "")
            )
        else:
            return None
    elif category == "vr":
        return VRSocket(config)
    else:
        raise HTTPException(400, "类别错误")

# 获取数据库连接
def get_db_conn():
    db_path = os.path.join(os.path.dirname(__file__), "teleop_data.db")
    return sqlite3.connect(db_path)

app = FastAPI()

CONFIG_PATH = "config.yaml"
DB_PATH = "teleop_data.db"


# 适配类型及对应config字段定义
ADAPTED_TYPES = {
    "arm": {
        "RealMan": ["ip", "port"],
        "TestArm": ["ip", "port", "model"]
    },
    "camera": {
        "RealSense": ["camera_type", "camera_position", "camera_serial"],
        "TestCam": ["camera_type", "camera_position"]
    },
    "vr": {
        "Quest": ["ip", "port"],
        "TestVR": ["ip", "port", "version"]
    }
}

# 全局设备池
device_pool = {
    "vr": {},         # {id: VRSocket实例}
    "arm": {},        # {id: RM_controller实例}
    "camera": {}      # {id: Camera实例}
}





# 1. 获取所有设备 type+config
@app.get("/devices")
def get_all_devices():
    conn = get_db_conn()
    cursor = conn.cursor()
    result = {"arm": [], "camera": [], "vr": []}
    for table, key in [("robotic_arm", "arm"), ("camera", "camera"), ("vr_headset", "vr")]:
        cursor.execute(f"SELECT id, type, config FROM {table} WHERE is_active=1")
        rows = cursor.fetchall()
        for r in rows:
            result[key].append({"id": r[0], "type": r[1], "config": json.loads(r[2])})
    conn.close()
    return result


# 获取适配类型及config字段
@app.get("/device/{category}/adapted_types")
def get_adapted_types(category: str):
    if category not in ADAPTED_TYPES:
        raise HTTPException(400, "类别错误")
    return ADAPTED_TYPES[category]

# 新增设备（卡片添加）
@app.post("/device/{category}/add")
def add_device(category: str, body: dict = Body(...)):
    type_ = body.get("type")
    config = body.get("config")
    if not type_ or not config:
        raise HTTPException(400, "缺少 type 或 config")
    # 只允许选择已适配类型
    if category not in ADAPTED_TYPES or type_ not in ADAPTED_TYPES[category]:
        raise HTTPException(400, f"类型 {type_} 未适配于 {category}")
    # 检查config字段
    required_fields = ADAPTED_TYPES[category][type_]
    for field in required_fields:
        if field not in config:
            raise HTTPException(400, f"缺少配置字段: {field}")
    table = get_table_name(category)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO {table} (type, config) VALUES (?, ?)", (type_, json.dumps(config)))
    conn.commit()
    conn.close()
    return {"msg": "设备已添加"}

# 获取单个设备详情
@app.get("/device/{category}/{id}")
def get_device(category: str, id: int):
    table = get_table_name(category)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id, type, config FROM {table} WHERE id=?", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "设备不存在")
    return {"id": row[0], "type": row[1], "config": json.loads(row[2])}


# 2. 修改某个设备 config
@app.put("/device/{category}/{id}/config")
def update_device_config(category: str, id: int, body: dict = Body(...)):
    config = body.get("config")
    if not config:
        raise HTTPException(400, "缺少 config")
    # 获取设备类型
    table = get_table_name(category)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT type FROM {table} WHERE id=?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "设备不存在")
    type_ = row[0]
    # 只允许选择已适配类型
    if category not in ADAPTED_TYPES or type_ not in ADAPTED_TYPES[category]:
        conn.close()
        raise HTTPException(400, f"类型 {type_} 未适配于 {category}")
    # 检查config字段
    required_fields = ADAPTED_TYPES[category][type_]
    for field in required_fields:
        if field not in config:
            conn.close()
            raise HTTPException(400, f"缺少配置字段: {field}")
    cursor.execute(f"UPDATE {table} SET config=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (json.dumps(config), id))
    conn.commit()
    conn.close()
    # 若对象已启动则同步更新对象 config
    if id in device_pool.get(category, {}):
        device = device_pool[category][id]
        if hasattr(device, 'update_config'):
            device.update_config(config)
    return {"msg": "配置已更新"}

# 3. 启动设备对象
@app.post("/device/{category}/{id}/start")
def start_device(category: str, id: int):
    table = get_table_name(category)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT type, config FROM {table} WHERE id=? AND is_active=1", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "设备不存在或未启用")
    type_, config = row[0], json.loads(row[1])
    # 初始化对象
    obj = create_device_instance(category, type_, config)
    if obj and hasattr(obj, 'start'):
        obj.start()
    device_pool[category][id] = obj
    return {"msg": "设备已启动"}

# 4. 停止并删除设备对象
@app.post("/device/{category}/{id}/stop")
def stop_device(category: str, id: int):
    pool = device_pool.get(category, {})
    if id not in pool:
        raise HTTPException(404, "设备未启动")
    obj = pool[id]
    if hasattr(obj, 'stop'):
        obj.stop()
    del pool[id]
    return {"msg": "设备已停止并删除"}


# 5. 删除设备（彻底从数据库移除）
@app.delete("/device/{category}/{id}/delete")
def delete_device(category: str, id: int):
    table = get_table_name(category)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id FROM {table} WHERE id=?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "设备不存在")
    cursor.execute(f"DELETE FROM {table} WHERE id=?", (id,))
    conn.commit()
    conn.close()
    # 同时从设备池移除对象（如果有）
    if id in device_pool.get(category, {}):
        del device_pool[category][id]
    return {"msg": "设备已彻底删除"}

# 获取设备连接状态
@app.get("/device/{category}/{id}/conn_status")
def get_device_conn_status(category: str, id: int):
    pool = device_pool.get(category, {})
    if id not in pool:
        return {"conn_status": 0}  # 未连接
    device = pool[id]
    if hasattr(device, 'get_conn_status'):
        status = device.get_conn_status()
    elif hasattr(device, 'is_connected'):
        # 兼容部分Camera类
        status = 1 if device.is_connected() else 2
    else:
        status = 0
    return {"conn_status": status}

app.mount("/", StaticFiles(directory="static"), name="index")

if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(__file__), "teleop_data.db")
    init_device_tables(db_path)
    # 配置Uvicorn参数
    uvicorn.run(
        app="server:app",  # 指明FastAPI应用的位置（模块名:应用实例名）
        host="0.0.0.0",  # 允许外部访问
        port=8000,       # 端口号
        reload=True,     # 开发模式下启用自动重载（生产环境建议关闭）
        workers=1        # 工作进程数（单进程即可，多进程可能影响WebSocket）
    )
    

# 启动命令: uvicorn server:app --reload