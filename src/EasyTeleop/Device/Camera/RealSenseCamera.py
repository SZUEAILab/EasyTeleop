import cv2
import numpy as np
from typing import Dict, Any, Tuple
import pyrealsense2 as rs
import threading
import time
# from pyorbbecsdk import *
from .BaseCamera import BaseCamera


class RealSenseCamera(BaseCamera):
    """RealSense摄像头设备实现"""
    
    # 定义需要的配置字段为静态字段
    name = "通用RealSense摄像头"
    description = "有线连接的RealSense摄像头设备"
    need_config = {
        "serial": {
            "type": "string",
            "description": "RealSense设备序列号"
        },
        "target_fps": {
            "type": "integer",
            "description": "目标帧率,0为不控制,默认30,但是注意D405摄像头同时使用两个需要设置为15",
            "default": 30
        },
    }
    
    @staticmethod
    def find_device():
        """
        查找可用的RealSense设备
        """
        context = rs.context()
        devices = context.query_devices()
        found = []
        # 打印设备信息并返回列表
        print("可用的设备:")
        for i, device in enumerate(devices):
            name = device.get_info(rs.camera_info.name)
            serial = device.get_info(rs.camera_info.serial_number)
            print(f"{i}: {name} - Serial: {serial}")
            found.append({"name": name, "serial": serial})
        return found
    def __init__(self, config: Dict[str, Any] = None):
        
        self.camera_serial = None
        self.pipeline = rs.pipeline() 
        self.rsconfig = rs.config()  
        # 子类字段初始化需要放在super()之前
        super().__init__(config)
        
        # 继承并扩展父类的事件
        self._events.update({
             "depth_frame": self._default_callback
        })
            
    def _main(self):
        try:
            last_time = time.time()
            
            color_frame, depth_frame = self.get_frames()
            self.emit("frame", color_frame)
            self.emit("depth_frame", depth_frame)

            # 只有当target_fps > 0时才进行帧率控制
            if self.target_fps > 0:
                # 帧率控制，而不是固定间隔
                current_time = time.time()
                elapsed = current_time - last_time
                if elapsed < self.min_interval:
                    time.sleep(self.min_interval - elapsed)
        except Exception as e:
            print(f"Error get camera frames: {str(e)}")
            self.set_conn_status(2)
            return

    def _connect_device(self) -> bool:
        """连接RealSense摄像头"""
        try:
            print(f"camera_serial: {self.camera_serial}")
            
            self.rsconfig.enable_device(self.camera_serial)
            self.rsconfig.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, self.target_fps)
            self.rsconfig.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, self.target_fps)
            self.profile = self.pipeline.start(self.rsconfig)
            # device = self.profile.get_device()
            # device.hardware_reset()
            print(f"connected successfully")
            return True
        except Exception as e:
            print(f"connect failed: {str(e)}")
            return False

    def _disconnect_device(self) -> bool:
        """断开RealSense摄像头连接"""
        try:
            if self.pipeline:
                self.pipeline.stop()
            print(f"disconnected successfully")
            return True
        except Exception as e:
            print(f"disconnect failed: {str(e)}")
            return False

    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        设置设备配置，验证配置是否符合need_config要求
        :param config: 配置字典
        :return: 是否设置成功
        """
        # 检查必需的配置字段
        for key in self.need_config:
            if key not in config:
                raise ValueError(f"缺少必需的配置字段: {key}")
        
        self.config = config
        self.camera_serial = config["serial"]
        self.target_fps = config["target_fps"]
        self.min_interval = 1.0 / self.target_fps if self.target_fps > 0 else 0
        
        return True
                

    def get_frames(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取RealSense摄像头帧(RGB, Depth)"""
        if self.get_conn_status() == 2:
            print("not connected")
            return None, None
        
        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        if not color_frame or not depth_frame:
            print(f"Failed to get frames from RealSense")
            return None, None
        return np.asanyarray(color_frame.get_data()), np.asanyarray(depth_frame.get_data())
