import logging
from typing import List, Dict, Any,Tuple
import numpy as np
import cv2
import time
from BaseCamera import BaseCamera
from RealSenseCamera import RealSenseCamera
# from OrbbecCamera import OrbbecCamera

CAMERA_SERIALS = {
    "RealSense": {
        'head': '153122070447',  
        'left_wrist': '427622270438',   
        'right_wrist': '427622270277',   
    }
}

class CameraManager:
    """摄像头管理器，负责初始化和管理多个摄像头实例"""

    # 创建一个从字符串到类的映射
    CAMERA_CLASSES = {
        "RealSense": RealSenseCamera,
        # "Orbbec": OrbbecCamera,
    }

    def __init__(self, camera_configs: List[Dict[str, str]]):
        """
        初始化CameraManager，并自动创建和注册摄像头
        """
        self._cameras: Dict[str, BaseCamera] = {}
        self._initialize_cameras(camera_configs)

    def _initialize_cameras(self, configs: List[Dict[str, str]]):
        """根据配置列表自动创建、连接和注册摄像头"""
        for config in configs:
            cam_type = config.get('type')
            cam_position = config.get('position')
            cam_serial = config.get('serial')

            if not cam_type or not cam_position or not cam_serial:
                print(f"Skipping invalid config: {config}")
                continue

            # 从映射中获取对应的摄像头类
            CameraClass = self.CAMERA_CLASSES.get(cam_type)

            if CameraClass:
                instance = CameraClass(camera_type=cam_type, camera_position=cam_position,camera_serial=cam_serial)
                if instance.connect():
                    self.register_camera(instance)
                else:
                    instance.logger_msg("failed to connect, will not be registered.")
            else:
                print(f"[CameraManager] Error: Camera type '{cam_type}' not recognized.")
    
    def get_cameras(self) -> List[BaseCamera]:
        """获取所有摄像头实例"""
        return self.cameras
    
    def register_camera(self, camera: BaseCamera):
        """注册一个摄像头实例"""
        key = f"{camera.camera_type}_{camera.camera_position}"
        if key not in self._cameras:
            self._cameras[key] = camera
            camera.logger_msg("registered successfully")
        else:
            camera.logger_msg("already registered")
    
    def get_frames(self) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """获取所有摄像头的帧数据
        数据格式：
        dict{
                "RealSense_head": (rgb_frame, depth_frame),
                "Orbbec_left_wrist": (rgb_frame, depth_frame),
                ...
            }
        
        """
        frames = {}
        for key, camera in self._cameras.items():
            if camera.is_connected():
                rgb_frame, depth_frame = camera.get_frames()
                frame_time = time.time()
                frames[key] = (rgb_frame, depth_frame, frame_time)
            else:
                camera.logger_msg("not connected, cannot get frames")
        return frames
    
if __name__ == "__main__":
    # 1. 只需要定义配置
    camera_configs = [
        {'type': 'RealSense', 'position': 'left_wrist', 'serial': '427622270438'},
        {'type': 'RealSense', 'position': 'right_wrist', 'serial': '427622270277'},
    ]

    # 2. 创建 Manager，它会自动完成所有初始化和连接工作
    print("Initializing Camera Manager...")
    manager = CameraManager(camera_configs)
    
    print("\n--- Starting frame acquisition loop ---")
    # 3. 直接开始使用
    try:
        while True:
            all_frames = manager.get_frames()

            for key, (rgb_frame, depth_frame,frame_time) in all_frames.items():
                if rgb_frame is not None:
                    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_frame, alpha=0.03), cv2.COLORMAP_JET)
                    images = np.hstack((rgb_frame, depth_colormap))
                    cv2.imshow(key, images)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        print("\n--- Cleaning up ---")
        # 断开所有摄像头连接
        for cam in manager.get_cameras():
            cam.disconnect()
        cv2.destroyAllWindows()

