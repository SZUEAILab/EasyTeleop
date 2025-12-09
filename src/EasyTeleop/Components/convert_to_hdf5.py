#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import h5py
import numpy as np
import cv2
import csv
import argparse
from pathlib import Path
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_states_from_csv(csv_path):
    """
    从CSV文件加载机械臂状态数据
    
    Args:
        csv_path (str): CSV文件路径
        
    Returns:
        list: 状态数据列表，每个元素为(timestamp, state_dict)
    """
    states = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # 跳过标题行
            for row in reader:
                timestamp = float(row[0])
                # 将字符串状态转换为字典或列表
                try:
                    state = eval(row[1])  # 注意：在生产环境中应使用更安全的方法如json.loads
                except:
                    state = row[1]  # 如果无法解析，则保持为字符串
                states.append((timestamp, state))
        logger.info(f"从 {csv_path} 加载了 {len(states)} 条状态数据")
    except Exception as e:
        logger.error(f"读取状态文件失败 {csv_path}: {e}")
    return states

def load_images_from_directory(image_dir):
    """
    从目录加载所有图像文件
    
    Args:
        image_dir (str): 图像目录路径
        
    Returns:
        list: 图像数据列表，每个元素为(timestamp, image_data)
    """
    images = []
    try:
        for image_file in sorted(os.listdir(image_dir)):
            if image_file.endswith(('.jpg', '.jpeg', '.png')):
                # 从文件名提取时间戳
                timestamp_str = image_file.split('_')[1].split('.')[0]
                timestamp = float(timestamp_str)
                
                image_path = os.path.join(image_dir, image_file)
                # 读取图像数据
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                images.append((timestamp, image_data))
        logger.info(f"从 {image_dir} 加载了 {len(images)} 张图像")
    except Exception as e:
        logger.error(f"读取图像目录失败 {image_dir}: {e}")
    return images

def create_hdf5_dataset(session_dir, output_hdf5_path):
    """
    将采集会话数据转换为HDF5格式
    
    Args:
        session_dir (str): 采集会话目录路径
        output_hdf5_path (str): 输出HDF5文件路径
    """
    try:
        # 获取图像和状态文件路径
        frames_dir = os.path.join(session_dir, 'frames')
        states_file = os.path.join(session_dir, 'states.csv')
        
        # 检查输入目录是否存在
        if not os.path.exists(frames_dir):
            logger.error(f"图像目录不存在: {frames_dir}")
            return False
            
        if not os.path.exists(states_file):
            logger.error(f"状态文件不存在: {states_file}")
            return False
        
        # 加载数据
        states = load_states_from_csv(states_file)
        images = load_images_from_directory(frames_dir)
        
        if not states or not images:
            logger.error("没有足够的数据来创建HDF5文件")
            return False
        
        # 创建HDF5文件
        with h5py.File(output_hdf5_path, 'w') as hdf5_file:
            # 创建基本结构
            observations_group = hdf5_file.create_group('observations')
            images_group = observations_group.create_group('images')
            action_group = hdf5_file.create_group('action')
            
            # 保存状态数据
            if states:
                timestamps, state_data = zip(*states)
                observations_group.create_dataset('qpos', data=state_data)
                hdf5_file.create_dataset('timestamps', data=timestamps)
            
            # 保存图像数据
            if images:
                timestamps, image_data = zip(*images)
                # 假设所有图像都是来自同一个摄像头
                # 在实际应用中，您可能需要根据文件名或其他信息区分不同摄像头
                images_group.create_dataset('cam_wrist', data=np.array(image_data, dtype=h5py.string_dtype()))
            
            # 添加元数据
            hdf5_file.attrs['num_samples'] = len(states)
            hdf5_file.attrs['description'] = 'Teleoperation data'
            hdf5_file.attrs['created_with'] = 'RealMan Teleoperate System'
            
        logger.info(f"成功创建HDF5文件: {output_hdf5_path}")
        return True
        
    except Exception as e:
        logger.error(f"创建HDF5文件失败: {e}")
        return False

def process_all_sessions(datasets_dir, output_dir):
    """
    处理所有采集会话并转换为HDF5格式
    
    Args:
        datasets_dir (str): 数据集根目录
        output_dir (str): HDF5文件输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 遍历所有会话目录
    for session_name in os.listdir(datasets_dir):
        session_dir = os.path.join(datasets_dir, session_name)
        if os.path.isdir(session_dir):
            logger.info(f"处理会话: {session_name}")
            
            # 输出HDF5文件路径
            output_hdf5_path = os.path.join(output_dir, f"{session_name}.hdf5")
            
            # 转换数据
            if create_hdf5_dataset(session_dir, output_hdf5_path):
                logger.info(f"会话 {session_name} 转换完成")
            else:
                logger.error(f"会话 {session_name} 转换失败")

def main():
    parser = argparse.ArgumentParser(description='将采集数据转换为HDF5格式')
    parser.add_argument('--input', '-i', type=str, required=True, 
                        help='输入数据集目录路径')
    parser.add_argument('--output', '-o', type=str, default='databases', 
                        help='输出HDF5文件目录路径 (默认: databases)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        logger.error(f"输入目录不存在: {args.input}")
        return
    
    logger.info(f"开始转换数据从 {args.input} 到 {args.output}")
    process_all_sessions(args.input, args.output)
    logger.info("数据转换完成")

if __name__ == '__main__':
    main()