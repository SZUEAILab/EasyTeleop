import cv2
import numpy as np
from typing import Dict, Any, Tuple
import pyrealsense2 as rs
from pyorbbecsdk import *
from BaseCamera import BaseCamera,CAMERA_SERIALS

class RealSenseCamera(BaseCamera):
    """RealSense摄像头设备实现"""
    
    def __init__(self, camera_type: str, camera_position:str, camera_serial: str):
        super().__init__(camera_type, camera_position, camera_serial)
        self.pipeline = None    # 存储pipeline对象
        self.config = rs.config()  
    
    def connect(self, **kwargs) -> bool:
        """连接RealSense摄像头"""
        try:
            self.pipeline = rs.pipeline()
            self.config.enable_device(CAMERA_SERIALS[self.camera_type][self.camera_position])
            self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            self.pipeline.start(self.config)
            self.logger_msg(f"connected successfully")
            return True
        except Exception as e:
            self.logger_msg(f"connect failed: {str(e)}")
            return False
    
    def disconnect(self) -> bool:
        """断开RealSense摄像头连接"""
        try:
            if self.pipeline:
                self.pipeline.stop()
                self.pipeline = None
            self.logger_msg(f"disconnected successfully")
            return True
        except Exception as e:
            self.logger_msg(f"disconnect failed: {str(e)}")
            return False
    
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
            self.logger_msg("not connected")
            return None, None
        
        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        if not color_frame or not depth_frame:
            self.logger_msg(f"Failed to get frames from RealSense")
            return None, None
        return np.asanyarray(color_frame.get_data()), np.asanyarray(depth_frame.get_data())



if __name__ == "__main__":
    camera1 = RealSenseCamera("RealSense", "left_wrist")
    camera2 = RealSenseCamera("RealSense", "right_wrist")
    camera1.connect()
    camera2.connect()
    for i in range(50):
            
            color_frame, depth_frame = camera1.get_frames()
            depth_frame = cv2.applyColorMap(cv2.convertScaleAbs(depth_frame, alpha=0.03), cv2.COLORMAP_JET)
            color_frame2, depth_frame2 = camera2.get_frames() # depth_image = cv.applyColorMap(cv.convertScaleAbs(depth_image, alpha=0.03), cv.COLORMAP_JET)
            depth_frame2 = cv2.applyColorMap(cv2.convertScaleAbs(depth_frame2, alpha=0.03), cv2.COLORMAP_JET)
            
            if color_frame is not None and depth_frame is not None:
                try:
                    cv2.imshow("Color", color_frame)
                    cv2.imshow("Depth", depth_frame)
                    cv2.waitKey(500)
                except cv2.error as e:
                    print(f"Display error (but frames are OK): {e}")
            if color_frame2 is not None and depth_frame2 is not None:
                try:
                    cv2.imshow("Color2", color_frame2)
                    cv2.imshow("Depth2", depth_frame2)
                    cv2.waitKey(500)
                except cv2.error as e:
                    print(f"Display error (but frames are OK): {e}")
        