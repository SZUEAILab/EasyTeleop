import cv2
import numpy as np
from typing import Dict, Any, Tuple
import pyrealsense2 as rs
import threading
import time
# from pyorbbecsdk import *
from ..BaseDevice import BaseDevice


class RealSenseCamera(BaseDevice):
    """RealSense摄像头设备实现"""
    
    # 定义需要的配置字段为静态字段
    need_config = {
        "serial": "摄像头序列号"
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.camera_type = None
        self.camera_position = None
        self.camera_serial = None
        self.target_fps = 30  # 目标帧率
        self.min_interval = 1.0 / self.target_fps  # 最小间隔时间
        self.polling_thread = None
        self.polling_running = False
        self.pipeline = None    # 存储pipeline对象
        self.rsconfig = rs.config()  
        
        self._events = {
             "frame": self._default_callback,
        }
        
        # 如果提供了配置，则设置配置
        if config:
            self.set_config(config)
            
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
        
        return True

    def start(self):
        self.connect()
        print("Camera connect")
        self.start_polling()

    def connect(self) -> bool:
        """连接RealSense摄像头"""
        try:
            self.pipeline = rs.pipeline()
            self.rsconfig.enable_device(self.camera_serial)
            self.rsconfig.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            self.rsconfig.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            profile = self.pipeline.start(self.rsconfig)
            device = profile.get_device()
            device.hardware_reset()
            self.set_conn_status(1)
            print(f"connected successfully")
            return True
        except Exception as e:
            self.set_conn_status(2)
            print(f"connect failed: {str(e)}")
            return False

    def disconnect(self) -> bool:
        """断开RealSense摄像头连接"""
        try:
            if self.pipeline:
                self.pipeline.stop()
                self.pipeline = None
            self.set_conn_status(2)
            print(f"disconnected successfully")
            return True
        except Exception as e:
            self.set_conn_status(2)
            print(f"disconnect failed: {str(e)}")
            return False

    def start_polling(self):
        """启动状态轮询线程"""
        if not self.polling_running:
            self.polling_running = True
            self.polling_thread = threading.Thread(target=self._poll_state, daemon=True)
            self.polling_thread.start()

    def stop_polling(self):
        """停止状态轮询线程"""
        self.polling_running = False
        if self.polling_thread is not None:
            self.polling_thread.join()
            self.polling_thread = None

    def _poll_state(self):
        last_time = time.time()
        while self.polling_running:
            try:
                color_frame, depth_frame = self.get_frames()
                self.emit("frame",color_frame)
                
            except Exception as e:
                print(f"Error polling robot state: {str(e)}")
                break
            
            # 帧率控制，而不是固定间隔
            current_time = time.time()
            elapsed = current_time - last_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            last_time = time.time()

    def is_connected(self) -> bool:
        """检查RealSense摄像头是否连接"""
        return self.pipeline is not None

    def get_device_info(self) -> Dict[str, Any]:
        """获取RealSense摄像头信息"""
        if self.is_connected():
            return {
                "serial": self.camera_serial,
                "type": self.camera_type,
                "position": self.camera_position
            }
        return None

    def get_frames(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取RealSense摄像头帧(RGB, Depth)"""
        if not self.is_connected():
            print("not connected")
            return None, None
        
        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        if not color_frame or not depth_frame:
            print(f"Failed to get frames from RealSense")
            return None, None
        return np.asanyarray(color_frame.get_data()), np.asanyarray(depth_frame.get_data())

    def stop(self):
        """停止设备"""
        self.stop_polling()
        self.disconnect()

    def __del__(self):
        self.stop()