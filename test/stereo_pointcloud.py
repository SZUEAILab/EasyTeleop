import sys
import os

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Device.Camera.RealSenseCamera import RealSenseCamera
import numpy as np
import open3d as o3d
import pyrealsense2 as rs

def capture_point_cloud(camera, serial):
    """
    从指定的RealSense相机捕获点云数据
    
    Args:
        camera: RealSenseCamera对象
        serial: 相机序列号
    
    Returns:
        open3d.geometry.PointCloud: 点云对象
    """
    if camera.connect():
        print(f"成功连接到相机 {serial}")
        # 获取帧数据
        frames = camera.pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        
        if not depth_frame or not color_frame:
            print(f"无法从相机 {serial} 获取帧数据")
            camera.disconnect()
            return None
            
        # 创建点云处理器
        pc = rs.pointcloud()
        points = pc.calculate(depth_frame)
        
        # 获取点坐标
        vtx = np.asanyarray(points.get_vertices()).view(np.float32).reshape(-1, 3)
        
        # 创建Open3D点云对象
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(vtx)
        
        # 添加颜色信息
        color_data = np.asanyarray(color_frame.get_data())
        color_data = color_data.reshape(-1, 3)[:, ::-1] / 255.0  # BGR to RGB and normalize
        pcd.colors = o3d.utility.Vector3dVector(color_data)
        
        camera.disconnect()
        return pcd
    else:
        print(f"无法连接到相机 {serial}")
        return None

def filter_point_cloud(pcd, distance_threshold=1.0):
    """
    过滤点云，移除距离过远的点
    
    Args:
        pcd: 输入点云
        distance_threshold: 距离阈值（米）
    
    Returns:
        open3d.geometry.PointCloud: 过滤后的点云
    """
    # 计算点到原点的距离
    points = np.asarray(pcd.points)
    distances = np.linalg.norm(points, axis=1)
    
    # 过滤掉距离超过阈值的点
    mask = distances < distance_threshold
    filtered_points = points[mask]
    
    # 如果点云有颜色信息，也过滤颜色
    if pcd.has_colors():
        colors = np.asarray(pcd.colors)
        filtered_colors = colors[mask]
        
        # 创建过滤后的点云
        filtered_pcd = o3d.geometry.PointCloud()
        filtered_pcd.points = o3d.utility.Vector3dVector(filtered_points)
        filtered_pcd.colors = o3d.utility.Vector3dVector(filtered_colors)
        return filtered_pcd
    else:
        # 创建过滤后的点云（无颜色信息）
        filtered_pcd = o3d.geometry.PointCloud()
        filtered_pcd.points = o3d.utility.Vector3dVector(filtered_points)
        return filtered_pcd

def downsample_point_cloud(pcd, voxel_size=0.01):
    """
    对点云进行下采样以减少点数
    
    Args:
        pcd: 输入点云
        voxel_size: 体素大小
    
    Returns:
        open3d.geometry.PointCloud: 下采样后的点云
    """
    return pcd.voxel_down_sample(voxel_size=voxel_size)

def register_point_clouds(source_pcd, target_pcd):
    """
    使用ICP算法配准两个点云
    
    Args:
        source_pcd: 源点云（将被变换）
        target_pcd: 目标点云（保持不动）
    
    Returns:
        open3d.geometry.PointCloud: 配准后的源点云
        numpy.ndarray: 变换矩阵
    """
    # 创建初始变换矩阵（单位矩阵）
    initial_transform = np.identity(4)
    
    # 使用ICP算法进行配准
    result = o3d.pipelines.registration.registration_icp(
        source_pcd, target_pcd, 0.05, initial_transform,
        o3d.pipelines.registration.TransformationEstimationPointToPoint()
    )
    
    # 应用变换
    transformed_pcd = source_pcd.transform(result.transformation)
    
    return transformed_pcd, result.transformation

def merge_point_clouds(pcd_list):
    """
    合并多个点云
    
    Args:
        pcd_list: 点云列表
    
    Returns:
        open3d.geometry.PointCloud: 合并后的点云
    """
    merged_pcd = o3d.geometry.PointCloud()
    for pcd in pcd_list:
        merged_pcd += pcd
    return merged_pcd

def save_point_cloud(pcd, filename):
    """
    保存点云到文件
    
    Args:
        pcd: 要保存的点云
        filename: 保存的文件名
        
    Returns:
        bool: 保存是否成功
    """
    try:
        # 确保文件路径存在
        save_dir = os.path.dirname(filename)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # 保存点云
        success = o3d.io.write_point_cloud(filename, pcd)
        if success:
            print(f"点云已保存到: {filename}")
        else:
            print(f"点云保存失败: {filename}")
        return success
    except Exception as e:
        print(f"保存点云时发生错误: {e}")
        return False

def main():
    # 相机序列号配置
    CAMERA_SERIALS = {
        'left_wrist': '427622270438',
        'right_wrist': '427622270277',
    }
    
    # 创建相机对象
    left_camera = RealSenseCamera({"serial": CAMERA_SERIALS['left_wrist']})
    right_camera = RealSenseCamera({"serial": CAMERA_SERIALS['right_wrist']})
    
    # 分别捕获左右相机的点云
    print("正在捕获左相机点云...")
    left_pcd = capture_point_cloud(left_camera, CAMERA_SERIALS['left_wrist'])
    
    print("正在捕获右相机点云...")
    right_pcd = capture_point_cloud(right_camera, CAMERA_SERIALS['right_wrist'])
    
    if left_pcd is None or right_pcd is None:
        print("无法从一个或两个相机获取点云数据")
        return
    
    # 显示原始点云信息
    print(f"左相机点云点数: {len(left_pcd.points)}")
    print(f"右相机点云点数: {len(right_pcd.points)}")
    
    # 可视化原始点云
    print("显示原始点云...")
    o3d.visualization.draw_geometries([left_pcd], window_name='Left Camera Point Cloud')
    o3d.visualization.draw_geometries([right_pcd], window_name='Right Camera Point Cloud')
    
    # 过滤点云（移除距离过远的点）
    print("过滤点云...")
    left_filtered = filter_point_cloud(left_pcd, distance_threshold=0.5)
    right_filtered = filter_point_cloud(right_pcd, distance_threshold=0.5)
    
    print(f"左相机过滤后点数: {len(left_filtered.points)}")
    print(f"右相机过滤后点数: {len(right_filtered.points)}")
    
    # 下采样点云
    print("下采样点云...")
    left_downsampled = downsample_point_cloud(left_filtered, voxel_size=0.0001)
    right_downsampled = downsample_point_cloud(right_filtered, voxel_size=0.0001)
    
    print(f"左相机下采样后点数: {len(left_downsampled.points)}")
    print(f"右相机下采样后点数: {len(right_downsampled.points)}")
    
    # 可视化处理后的点云
    print("显示处理后的点云...")
    o3d.visualization.draw_geometries([left_downsampled], window_name='Processed Left Point Cloud')
    o3d.visualization.draw_geometries([right_downsampled], window_name='Processed Right Point Cloud')
    
    # 配准点云（将右相机点云配准到左相机点云坐标系）
    print("正在进行点云配准...")
    right_registered, transformation = register_point_clouds(right_downsampled, left_downsampled)
    print("点云配准完成")
    print(f"变换矩阵:\n{transformation}")
    
    # 可视化配准后的点云
    print("显示配准后的点云...")
    o3d.visualization.draw_geometries([left_downsampled, right_registered], 
                                    window_name='Registered Point Clouds')
    
    # 合并点云
    print("正在合并点云...")
    merged_pcd = merge_point_clouds([left_downsampled, right_registered])
    print(f"合并后点云点数: {len(merged_pcd.points)}")
    
    # 显示最终合并的点云
    print("显示合并后的点云...")
    o3d.visualization.draw_geometries([merged_pcd], window_name='Merged Point Cloud')
    
    # 保存点云
    timestamp = int(np.floor(time.time()))
    
    save_point_cloud(left_pcd, f"datasets/left_original_{timestamp}.pcd")
    save_point_cloud(right_pcd, f"datasets/right_original_{timestamp}.pcd")
    
    save_point_cloud(left_filtered, f"datasets/left_filtered_{timestamp}.pcd")
    save_point_cloud(right_filtered, f"datasets/right_filtered_{timestamp}.pcd")
    
    save_point_cloud(left_downsampled, f"datasets/left_processed_{timestamp}.pcd")
    save_point_cloud(right_downsampled, f"datasets/right_processed_{timestamp}.pcd")
    
    save_point_cloud(right_registered, f"datasets/right_registered_{timestamp}.pcd")
    save_point_cloud(merged_pcd, f"datasets/merged_{timestamp}.pcd")
    
    print("所有点云已保存完成")

if __name__ == "__main__":
    import time
    main()