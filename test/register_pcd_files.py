import numpy as np
import open3d as o3d
import os

def load_point_cloud(filename):
    """
    从PCD文件加载点云数据
    
    Args:
        filename: PCD文件路径
    
    Returns:
        open3d.geometry.PointCloud: 点云对象
    """
    if not os.path.exists(filename):
        print(f"文件不存在: {filename}")
        return None
        
    pcd = o3d.io.read_point_cloud(filename)
    if len(pcd.points) == 0:
        print(f"点云文件为空: {filename}")
        return None
        
    print(f"成功加载点云: {filename}, 点数: {len(pcd.points)}")
    return pcd

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

def remove_planes(pcd, distance_threshold=0.01, ransac_n=3, num_iterations=1000):
    """
    移除点云中的主要平面（如桌面），以提高配准准确性
    
    Args:
        pcd: 输入点云
        distance_threshold: RANSAC平面分割距离阈值
        ransac_n: RANSAC每次迭代使用的点数
        num_iterations: RANSAC迭代次数
    
    Returns:
        open3d.geometry.PointCloud: 移除主要平面后的点云
    """
    # 创建点云副本
    pcd_copy = pcd.select_by_index(list(range(len(pcd.points))))
    
    # 估计法向量
    pcd_copy.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(
        radius=0.02, max_nn=30))
    
    # 使用RANSAC分割平面
    plane_model, inliers = pcd_copy.segment_plane(distance_threshold=distance_threshold,
                                                  ransac_n=ransac_n,
                                                  num_iterations=num_iterations)
    
    # 获取平面外的点（非平面点）
    outlier_cloud = pcd_copy.select_by_index(inliers, invert=True)
    
    print(f"原始点云点数: {len(pcd.points)}")
    print(f"平面内点数: {len(inliers)}")
    print(f"平面外点数: {len(outlier_cloud.points)}")
    
    return outlier_cloud

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

def preprocess_point_cloud(pcd, voxel_size):
    """
    预处理点云：下采样、估计法向量、计算FPFH特征
    
    Args:
        pcd: 输入点云
        voxel_size: 体素大小
    
    Returns:
        open3d.geometry.PointCloud: 预处理后的点云
        open3d.pipelines.registration.Feature: FPFH特征
    """
    # 下采样
    pcd_down = pcd.voxel_down_sample(voxel_size)
    
    # 估计法向量
    radius_normal = voxel_size * 20
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30)
    )
    
    # 计算FPFH特征
    radius_feature = voxel_size * 50
    fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_feature, max_nn=100)
    )
    
    return pcd_down, fpfh

def execute_global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size):
    """
    执行全局配准
    
    Args:
        source_down: 源点云（下采样后）
        target_down: 目标点云（下采样后）
        source_fpfh: 源点云FPFH特征
        target_fpfh: 目标点云FPFH特征
        voxel_size: 体素大小
    
    Returns:
        open3d.pipelines.registration.RegistrationResult: 配准结果
    """
    distance_threshold = voxel_size * 1.5
    # 改进RANSAC参数以获得更准确的初始对齐
    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down, target_down, source_fpfh, target_fpfh, True,  # True表示使用6自由度变换(包括旋转)
        distance_threshold,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        4, [  # 增加检查器数量以提高准确性
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(distance_threshold)
        ], 
        o3d.pipelines.registration.RANSACConvergenceCriteria(4000000, 0.999)  # 增加迭代次数以更好地处理180度旋转
    )
    return result

def refine_registration(source_pcd, target_pcd, init_transform, voxel_size):
    """
    精细化配准
    
    Args:
        source_pcd: 源点云
        target_pcd: 目标点云
        init_transform: 初始变换矩阵
        voxel_size: 体素大小
    
    Returns:
        open3d.pipelines.registration.RegistrationResult: 精细化配准结果
    """
    # 使用多尺度ICP提高精度
    distance_threshold = voxel_size * 0.4
    result = o3d.pipelines.registration.registration_icp(
        source_pcd, target_pcd, distance_threshold, init_transform,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=100)
    )
    return result

def advanced_register_point_clouds(source_pcd, target_pcd):
    """
    使用高级方法配准两个点云（全局配准+ICP细化）
    
    Args:
        source_pcd: 源点云（将被变换）
        target_pcd: 目标点云（保持不动）
    
    Returns:
        open3d.geometry.PointCloud: 配准后的源点云
        numpy.ndarray: 变换矩阵
    """
    voxel_size = 0.005  # 5mm
    
    # 预处理点云
    print("预处理点云...")
    source_down, source_fpfh = preprocess_point_cloud(source_pcd, voxel_size)
    target_down, target_fpfh = preprocess_point_cloud(target_pcd, voxel_size)
    
    # 全局配准
    print("执行全局配准...")
    global_result = execute_global_registration(source_down, target_down, 
                                              source_fpfh, target_fpfh, voxel_size)
    print(f"全局配准结果: fitness={global_result.fitness}, rmse={global_result.inlier_rmse}")
    
    # 精细化配准 - 使用多步骤优化
    print("执行精细化配准...")
    # 第一步：使用较大阈值进行粗略优化
    refined_result1 = refine_registration(source_pcd, target_pcd, 
                                        global_result.transformation, voxel_size*2)
    
    # 第二步：使用较小阈值进行精细优化
    refined_result2 = refine_registration(source_pcd, target_pcd, 
                                        refined_result1.transformation, voxel_size)
    
    # 应用最终变换
    transformed_pcd = source_pcd.transform(refined_result2.transformation)
    
    return transformed_pcd, refined_result2.transformation

def main():
    # PCD文件路径配置
    left_pcd_file = "test/left_original_1757851577.pcd"  # 示例路径，请根据实际文件路径修改
    right_pcd_file = "test/right_original_1757851577.pcd"  # 示例路径，请根据实际文件路径修改
    
    # 检查文件是否存在
    if not os.path.exists(left_pcd_file):
        print(f"左眼点云文件不存在: {left_pcd_file}")
        return
        
    if not os.path.exists(right_pcd_file):
        print(f"右眼点云文件不存在: {right_pcd_file}")
        return
    
    # 从PCD文件加载点云
    print("正在加载左眼点云...")
    left_pcd = load_point_cloud(left_pcd_file)
    
    print("正在加载右眼点云...")
    right_pcd = load_point_cloud(right_pcd_file)
    
    if left_pcd is None or right_pcd is None:
        print("无法从一个或两个文件加载点云数据")
        return
    
    # 显示原始点云信息
    print(f"左眼点云点数: {len(left_pcd.points)}")
    print(f"右眼点云点数: {len(right_pcd.points)}")
    
    # 可视化原始点云
    print("显示原始点云...")
    o3d.visualization.draw_geometries([left_pcd], window_name='Left Eye Point Cloud')
    o3d.visualization.draw_geometries([right_pcd], window_name='Right Eye Point Cloud')
    
    # 过滤点云（移除距离过远的点）
    print("过滤点云...")
    left_filtered = filter_point_cloud(left_pcd, distance_threshold=0.5)
    right_filtered = filter_point_cloud(right_pcd, distance_threshold=0.5)
    
    print(f"左眼过滤后点数: {len(left_filtered.points)}")
    print(f"右眼过滤后点数: {len(right_filtered.points)}")
    
    # 移除主要平面（如桌面）以提高配准准确性
    print("移除点云中的主要平面...")
    left_no_plane = remove_planes(left_filtered, distance_threshold=0.01)
    right_no_plane = remove_planes(right_filtered, distance_threshold=0.01)
    
    # 下采样点云
    print("下采样点云...")
    left_downsampled = downsample_point_cloud(left_no_plane, voxel_size=0.005)
    right_downsampled = downsample_point_cloud(right_no_plane, voxel_size=0.005)
    
    print(f"左眼下采样后点数: {len(left_downsampled.points)}")
    print(f"右眼下采样后点数: {len(right_downsampled.points)}")
    
    # 可视化处理后的点云
    print("显示处理后的点云...")
    o3d.visualization.draw_geometries([left_downsampled], window_name='Processed Left Point Cloud')
    o3d.visualization.draw_geometries([right_downsampled], window_name='Processed Right Point Cloud')
    
    # 使用高级配准方法（将右眼点云配准到左眼点云坐标系）
    print("正在进行点云配准...")
    right_registered, transformation = advanced_register_point_clouds(right_downsampled, left_downsampled)
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

if __name__ == "__main__":
    main()