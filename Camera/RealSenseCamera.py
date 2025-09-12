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
    
    def __init__(self, config: str, poll_interval=0.01):
        super().__init__(config)
        self.poll_interval = poll_interval  # 轮询间隔（秒）
        self.polling_thread = None
        self.polling_running = False
        self.pipeline = None    # 存储pipeline对象
        self.rsconfig = rs.config()  
        
        self._events = {
             "frame": self._default_callback,
        }

    def start(self):
        self.connect()
        print("Camera connect")
        self.start_polling()

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
        while self.polling_running:
            try:
                color_frame, depth_frame = self.get_frames()
                self.emit("frame",color_frame)
                
            except Exception as e:
                print(f"Error polling robot state: {str(e)}")
                break
            
            time.sleep(self.poll_interval)
    
    def connect(self) -> bool:
        """连接RealSense摄像头"""
        try:
            self.pipeline = rs.pipeline()
            self.rsconfig.enable_device(self.config["serial"])
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
        """断开RealSense摄像头连接"""
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



# if __name__ == "__main__":
#     CAMERA_SERIALS = {
#     "RealSense": {
#         'head': '153122070447',  
#         'left_wrist': '427622270438',   
#         'right_wrist': '427622270277',   
#     }
# }
#     camera1 = RealSenseCamera({"serial":"153122070447"})
#     camera1.connect()
#     while 1:
            
#         color_frame, depth_frame = camera1.get_frames()
#         depth_frame = cv2.applyColorMap(cv2.convertScaleAbs(depth_frame, alpha=0.03), cv2.COLORMAP_JET)
        
#         if color_frame is not None and depth_frame is not None:
#             try:
#                 cv2.imshow("Color", color_frame)
#                 cv2.imshow("Depth", depth_frame)
#                 cv2.waitKey(1)
#             except cv2.error as e:
#                 print(f"Display error (but frames are OK): {e}")
if __name__ == "__main__":
    import open3d as o3d
    CAMERA_SERIALS = {
        "RealSense": {
            'head': '153122070447',
            'left_wrist': '427622270438',
            'right_wrist': '427622270277',
        }
    }
    camera1 = RealSenseCamera({"serial": "153122070447"})
    if camera1.connect():
        pipeline = camera1.pipeline
        pc = rs.pointcloud()
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        points = pc.calculate(depth_frame)
        vtx = np.asanyarray(points.get_vertices()).view(np.float32).reshape(-1, 3)
        # 构建Open3D点云
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(vtx)
        o3d.visualization.draw_geometries([pcd], window_name='RealSense PointCloud')
        camera1.disconnect()