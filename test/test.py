import sys
import os

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Device.Camera.RealSenseCamera import RealSenseCamera
import numpy as np
import open3d as o3d
import pyrealsense2 as rs

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