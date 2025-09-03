import yaml
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import threading
import uvicorn  # 导入uvicorn

from Robots.RealMan import RM_controller
from VRSocket import VRSocket
from Teleoperation import Teleoperation

app = FastAPI()


CONFIG_PATH = "config.yaml"

class Config(BaseModel):
    vr_ip: str
    vr_port: int
    left_rm_ip: str
    right_rm_ip: str

class Status(BaseModel):
    vr_connected: bool
    left_rm_connected: bool
    right_rm_connected: bool
    teleop_running: bool

# 全局变量
config: Optional[Config] = None
vrsocket: Optional[VRSocket] = None
l_arm: Optional[RM_controller] = None
r_arm: Optional[RM_controller] = None
teleop: Optional[Teleoperation] = None
teleop_thread: Optional[threading.Thread] = None

status = Status(
    vr_connected=False,
    left_rm_connected=False,
    right_rm_connected=False,
    teleop_running=False
)

def save_config_to_yaml(cfg: Config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg.dict(), f)

def load_config_from_yaml():
    global config
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            config = Config(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置失败: {e}")

@app.post("/config")
def set_config(cfg: Config = Body(...)):
    global config
    config = cfg
    save_config_to_yaml(cfg)
    return {"msg": "配置已保存", "config": cfg.dict()}

@app.post("/connect/robot")
def connect_robot():
    global l_arm, r_arm, config, status
    if not config:
        load_config_from_yaml()
    if not config:
        raise HTTPException(status_code=400, detail="请先配置IP")
    try:
        l_arm = RM_controller(config.left_rm_ip)
        r_arm = RM_controller(config.right_rm_ip)
        status.left_rm_connected = True
        status.right_rm_connected = True
        return {"msg": "机器人连接成功"}
    except Exception as e:
        status.left_rm_connected = False
        status.right_rm_connected = False
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/connect/vr")
def connect_vr():
    global vrsocket, config, status
    if not config:
        load_config_from_yaml()
    if not config:
        raise HTTPException(status_code=400, detail="请先配置IP")
    try:
        vrsocket = VRSocket(config.vr_ip, config.vr_port)
        status.vr_connected = True
        return {"msg": "VR端连接成功"}
    except Exception as e:
        status.vr_connected = False
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
def get_status():
    return status.dict()

@app.post("/start_teleop")
def start_teleop():
    global teleop, vrsocket, l_arm, r_arm, status, teleop_thread
    if not (vrsocket and l_arm and r_arm):
        raise HTTPException(status_code=400, detail="请先连接VR和机器人")
    teleop = Teleoperation(left_wrist_controller=l_arm, right_wrist_controller=r_arm)
    @vrsocket.on_message
    def handle_message(msg):
        teleop.handle_socket_data(msg)
    vrsocket.start()
    def run_teleop():
        teleop.run()
    teleop_thread = threading.Thread(target=run_teleop, daemon=True)
    teleop_thread.start()
    status.teleop_running = True
    return {"msg": "遥操作已启动"}

app.mount("/", StaticFiles(directory="static"), name="index")

if __name__ == "__main__":
    # 配置Uvicorn参数
    uvicorn.run(
        app="server:app",  # 指明FastAPI应用的位置（模块名:应用实例名）
        host="0.0.0.0",  # 允许外部访问
        port=8000,       # 端口号
        reload=True,     # 开发模式下启用自动重载（生产环境建议关闭）
        workers=1        # 工作进程数（单进程即可，多进程可能影响WebSocket）
    )
    

# 启动命令: uvicorn server:app --reload