from TeleopGroup.BaseTeleopGroup import BaseTeleopGroup
import threading
import time
import logging

# 创建日志记录器
logger = logging.getLogger(__name__)

class DefaultTeleopGroup(BaseTeleopGroup):
    """默认遥操组类型，支持双臂+VR+3摄像头的标准配置"""
    
    # 遥操组类型名称
    name = "默认遥操组"
    
    # 遥操组类型描述
    description = "支持双臂+VR+3摄像头的标准配置"
    
    # 遥操组所需配置字段
    need_config = [
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

    def __init__(self, devices = None):
        super().__init__(devices)
        self.status_thread = None
        self.status_thread_running = False

    def start(self) -> bool:
        """
        启动默认遥操组
        :return: 是否启动成功
        """
        try:
            print("启动默认遥操组")
            
            # 启动数据采集
            self.data_collect.start()
            self.teleop.on("buttonATurnDown", self.data_collect.toggle_capture_state)
            # self.data_collect.on("status_change", None)
            
            # 注册回调函数
            if self.devices[0]:
                self.teleop.on("leftGripDown",self.devices[0].start_control)
                self.teleop.on("leftGripUp",self.devices[0].stop_control)
                self.devices[0].on("state", self.data_collect.put_robot_state)
            if self.devices[1]:
                self.teleop.on("rightGripDown",self.devices[1].start_control)
                self.teleop.on("rightGripUp",self.devices[1].stop_control)
                self.devices[1].on("state", self.data_collect.put_robot_state)

            self.devices[2].on("message",self.teleop.handle_socket_data)

            if self.devices[3]:
                self.devices[3].on("frame",self.data_collect.put_video_frame)
            if self.devices[4]:
                self.devices[4].on("frame",self.data_collect.put_video_frame)
            if self.devices[5]:
                self.devices[5].on("frame",self.data_collect.put_video_frame)
            
            # 启动所有设备
            for device in self.devices:
                if device:
                    device.start()
                
            self.running = True
            
            # 启动状态打印线程
            # self.status_thread_running = True
            # self.status_thread = threading.Thread(target=self._print_device_status, daemon=True)
            # self.status_thread.start()
            return True
        except Exception as e:
            print(f"启动默认遥操组失败: {e}")
            return False

    def stop(self) -> bool:
        """
        停止默认遥操组
        :return: 是否停止成功
        """
        try:
            print("停止默认遥操组")
            
            # 停止状态打印线程
            self.status_thread_running = False
            if self.status_thread and self.status_thread.is_alive():
                self.status_thread.join(timeout=2.0)
            
            # 停止所有设备
            for device in self.devices:
                if device:
                    device.stop()
            
            # 停止数据采集
            self.data_collect.stop()
            
            # 需要等待数采后处理完毕
            
            self.devices.clear()
            self.running = False
            return True
        except Exception as e:
            print(f"停止默认遥操组失败: {e}")
            return False

    def _print_device_status(self):
        """
        定期打印设备状态的线程函数
        """
        while self.status_thread_running and self.running:
            try:
                status_info = []
                for i, device in enumerate(self.devices):
                    if device:
                        status_info.append(f"Device[{i}]: {device.__class__.__name__}, Status: {device.get_conn_status()}")
                    else:
                        status_info.append(f"Device[{i}]: None")
                
                logger.info("设备状态: " + ", ".join(status_info))
            except Exception as e:
                logger.error(f"获取设备状态时出错: {e}")
            
            # 等待1秒
            time.sleep(1)
            