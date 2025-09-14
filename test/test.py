import sys
import os

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Device.Camera.RealSenseCamera import RealSenseCamera
import numpy as np
import open3d as o3d
import pyrealsense2 as rs
import cv2

if __name__ == "__main__":
    import open3d as o3d
    CAMERA_SERIALS = {
        "RealSense": {
            'head': '153122070447',
            'left_wrist': '427622270438',
            'right_wrist': '427622270277',
        }
    }
    camera1 = RealSenseCamera({"serial": "427622270438"})
    if camera1.connect():
        pipeline = camera1.pipeline
        pc = rs.pointcloud()
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        cv2.imshow("Color Frame", np.asanyarray(color_frame.get_data()))
        cv2.imshow("Depth Frame", np.asanyarray(depth_frame.get_data()))
        cv2.waitKey(0)
        points = pc.calculate(depth_frame)
        
        vtx = np.asanyarray(points.get_vertices()).view(np.float32).reshape(-1, 3)
        print(len(vtx))
        print(vtx[5555])
        
        # 创建原始点云的Open3D对象用于显示
        original_pcd = o3d.geometry.PointCloud()
        original_pcd.points = o3d.utility.Vector3dVector(vtx)
        
        # 显示原始点云
        o3d.visualization.draw_geometries([original_pcd], window_name='Original RealSense PointCloud')
        
        # 删除过远点云和进行下采样
        # 计算点到原点的距离
        distances = np.linalg.norm(vtx, axis=1)
        
        # 过滤掉距离超过0.5米的点
        mask = distances < 0.5
        filtered_vtx = vtx[mask]

        
        
        # 构建Open3D点云并进行下采样
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(filtered_vtx)

        # 修改: 将点云对象传递给draw_geometries而不是点的向量
        o3d.visualization.draw_geometries([pcd], window_name='Filtered RealSense PointCloud')
        
        # 使用voxel下采样减少点云数量
        downsampled_pcd = pcd.voxel_down_sample(voxel_size=0.005)
        
        print(f"原始点云数量: {len(vtx)}")
        print(f"过滤后点云数量: {len(filtered_vtx)}")
        print(f"下采样后点云数量: {len(downsampled_pcd.points)}")
        
        # 可视化处理后的点云
        o3d.visualization.draw_geometries([downsampled_pcd], window_name='Processed RealSense PointCloud')
        camera1.disconnect()