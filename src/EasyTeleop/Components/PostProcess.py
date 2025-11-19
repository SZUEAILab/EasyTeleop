import os
import json
import csv
import h5py
import numpy as np
from PIL import Image
from scipy.interpolate import interp1d
from collections import defaultdict
import argparse
import io


class DataPostProcessor:
    def __init__(self, temp_dir="datasets/temp", output_dir="datasets/hdf5"):
        """
        初始化后处理器
        
        Args:
            temp_dir (str): 临时数据目录路径
            output_dir (str): HDF5输出目录路径
        """
        self.temp_dir = temp_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def find_sessions(self):
        """
        查找所有可用的数据会话
        
        Returns:
            list: 会话目录列表
        """
        sessions = []
        for item in os.listdir(self.temp_dir):
            session_path = os.path.join(self.temp_dir, item)
            if os.path.isdir(session_path) and os.path.exists(os.path.join(session_path, "metadata.json")):
                sessions.append(item)
        return sessions
    
    def load_session_data(self, session_id):
        """
        加载指定会话的所有数据
        
        Args:
            session_id (str): 会话ID
            
        Returns:
            tuple: (metadata, image_data, arm_data)
        """
        session_path = os.path.join(self.temp_dir, session_id)
        
        # 加载元数据
        with open(os.path.join(session_path, "metadata.json"), "r", encoding="utf-8") as f:
            metadata = json.load(f)
            
        # 加载图像数据
        frames_path = os.path.join(session_path, "frames")
        image_data = {}
        if os.path.exists(frames_path):
            # 遍历所有摄像头目录
            for camera_dir in os.listdir(frames_path):
                camera_path = os.path.join(frames_path, camera_dir)
                if os.path.isdir(camera_path) and camera_dir.startswith("camera_"):
                    camera_id = int(camera_dir.split("_")[1])
                    if camera_id not in image_data:
                        image_data[camera_id] = {}
                    
                    for frame_file in os.listdir(camera_path):
                        if frame_file.startswith("frame_") and (frame_file.endswith(".png") or frame_file.endswith(".jpg")):
                            # 支持PNG和JPG格式
                            timestamp = float(frame_file[6:-4])  # 去掉"frame_"前缀和文件扩展名
                            image_data[camera_id][timestamp] = os.path.join(camera_path, frame_file)
                    
        # 加载双臂数据
        arm_data = {}
        for arm_id in [0, 1]:  # 支持两个臂
            arm_path = os.path.join(session_path, f"arm_{arm_id}")
            if os.path.exists(arm_path):
                arm_data[arm_id] = {"pose": {}, "joint": {}, "end_effector": {}}
                
                # 加载位姿数据
                pose_file = os.path.join(arm_path, "poses.csv")
                if os.path.exists(pose_file):
                    with open(pose_file, "r", encoding="utf-8") as f:
                        reader = csv.reader(f)
                        next(reader)  # 跳过标题行
                        for row in reader:
                            if len(row) >= 3:
                                timestamp = float(row[0])
                                index = int(row[1])
                                value = float(row[2])
                                
                                if timestamp not in arm_data[arm_id]["pose"]:
                                    arm_data[arm_id]["pose"][timestamp] = {}
                                    
                                arm_data[arm_id]["pose"][timestamp][index] = value
                
                # 加载关节数据
                joint_file = os.path.join(arm_path, "joints.csv")
                if os.path.exists(joint_file):
                    with open(joint_file, "r", encoding="utf-8") as f:
                        reader = csv.reader(f)
                        next(reader)  # 跳过标题行
                        for row in reader:
                            if len(row) >= 3:
                                timestamp = float(row[0])
                                index = int(row[1])
                                value = float(row[2])
                                
                                if timestamp not in arm_data[arm_id]["joint"]:
                                    arm_data[arm_id]["joint"][timestamp] = {}
                                    
                                arm_data[arm_id]["joint"][timestamp][index] = value
                
                # 加载末端执行器数据
                end_effector_file = os.path.join(arm_path, "end_effector.csv")
                if os.path.exists(end_effector_file):
                    with open(end_effector_file, "r", encoding="utf-8") as f:
                        reader = csv.reader(f)
                        next(reader)  # 跳过标题行
                        for row in reader:
                            if len(row) >= 3:
                                timestamp = float(row[0])
                                index = row[1]  # 末端执行器数据的索引可能是字符串
                                value = float(row[2])
                                
                                if timestamp not in arm_data[arm_id]["end_effector"]:
                                    arm_data[arm_id]["end_effector"][timestamp] = {}
                                    
                                arm_data[arm_id]["end_effector"][timestamp][index] = value
                    
        return metadata, image_data, arm_data
    
    def interpolate_states(self, image_timestamps, state_timestamps, state_values):
        """
        对状态数据进行插值以匹配图像时间戳
        
        Args:
            image_timestamps (list): 图像时间戳列表
            state_timestamps (list): 状态时间戳列表
            state_values (np.array): 状态值数组
            
        Returns:
            np.array: 插值后的状态值数组
        """
        if len(state_timestamps) < 2:
            # 如果状态点少于2个，无法插值，复制最近的状态值
            if len(state_timestamps) == 1:
                return np.tile(state_values[0], (len(image_timestamps), 1))
            else:
                # 如果没有状态数据，返回零值
                num_dims = state_values.shape[1] if state_values.size > 0 else 6  # 默认6个维度
                return np.zeros((len(image_timestamps), num_dims))
                
        # 创建插值函数
        f_values = interp1d(state_timestamps, state_values, axis=0, kind='linear', 
                              bounds_error=False, fill_value=(state_values[0], state_values[-1]))
        
        # 对图像时间戳进行插值
        interpolated_states = f_values(image_timestamps)
        return interpolated_states
    
    def process_session_to_hdf5(self, session_id, output_file=None):
        """
        将指定会话的数据处理为HDF5格式
        
        Args:
            session_id (str): 会话ID
            output_file (str): 输出HDF5文件路径，如果为None则自动生成
        """
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"{session_id}.hdf5")
            
        print(f"Processing session {session_id}...")
        
        # 加载会话数据
        metadata, image_data, arm_data = self.load_session_data(session_id)
        
        if not image_data:
            print(f"No image data found for session {session_id}")
            return
            
        if not arm_data:
            print(f"No arm data found for session {session_id}")
            return
            
        # 排序时间戳
        # 合并所有摄像头的时间戳并去重
        all_image_timestamps = set()
        for camera_id in image_data:
            all_image_timestamps.update(image_data[camera_id].keys())
        sorted_image_timestamps = sorted(list(all_image_timestamps))
        
        # 处理每个臂的数据
        processed_arm_data = {}
        for arm_id in arm_data:
            arm = arm_data[arm_id]
            sorted_pose_timestamps = sorted(arm["pose"].keys()) if arm["pose"] else []
            sorted_joint_timestamps = sorted(arm["joint"].keys()) if arm["joint"] else []
            sorted_end_effector_timestamps = sorted(arm["end_effector"].keys()) if arm["end_effector"] else []
            
            print(f"Arm {arm_id}: Found {len(sorted_pose_timestamps)} pose records, {len(sorted_joint_timestamps)} joint records, and {len(sorted_end_effector_timestamps)} end_effector records")
            
            # 确定维度
            pose_dim = 0
            joint_dim = 0
            end_effector_dim = 0
            
            # 通过检查所有时间戳的数据来确定维度
            if arm["pose"]:
                for pose_info in arm["pose"].values():
                    if pose_info:
                        pose_dim = max(pose_dim, max(pose_info.keys()) + 1)
                        
            if arm["joint"]:
                for joint_info in arm["joint"].values():
                    if joint_info:
                        joint_dim = max(joint_dim, max(joint_info.keys()) + 1)
                        
            if arm["end_effector"]:
                # 处理末端执行器数据维度（末端执行器数据可能是字符串索引）
                end_effector_keys = set()
                for end_effector_info in arm["end_effector"].values():
                    end_effector_keys.update(end_effector_info.keys())
                end_effector_dim = len(end_effector_keys)
                end_effector_key_to_index = {key: i for i, key in enumerate(sorted(end_effector_keys))}
            
            # 构建数据数组
            # 构建pose数组
            pose_data_list = []
            for timestamp in sorted_pose_timestamps:
                pose_info = arm["pose"][timestamp]
                # 构建pose数组
                pose_array = [0.0] * pose_dim
                for i in range(pose_dim):
                    if i in pose_info:
                        pose_array[i] = pose_info[i]
                pose_data_list.append(pose_array)
                
            # 构建joint数组
            joint_data_list = []
            for timestamp in sorted_joint_timestamps:
                joint_info = arm["joint"][timestamp]
                # 构建joint数组
                joint_array = [0.0] * joint_dim
                for i in range(joint_dim):
                    if i in joint_info:
                        joint_array[i] = joint_info[i]
                joint_data_list.append(joint_array)
                
            # 构建end_effector数组
            end_effector_data_list = []
            for timestamp in sorted_end_effector_timestamps:
                end_effector_info = arm["end_effector"][timestamp]
                # 构建end_effector数组
                end_effector_array = [0.0] * end_effector_dim
                for key, value in end_effector_info.items():
                    if key in end_effector_key_to_index:
                        index = end_effector_key_to_index[key]
                        end_effector_array[index] = value
                end_effector_data_list.append(end_effector_array)
                
            # 转换为numpy数组
            pose_data_array = np.array(pose_data_list) if pose_data_list else np.array([]).reshape(0, pose_dim or 6)
            joint_data_array = np.array(joint_data_list) if joint_data_list else np.array([]).reshape(0, joint_dim or 6)
            end_effector_data_array = np.array(end_effector_data_list) if end_effector_data_list else np.array([]).reshape(0, end_effector_dim or 1)
            
            # 对状态数据进行插值以匹配图像时间戳
            interp_poses = self.interpolate_states(sorted_image_timestamps, sorted_pose_timestamps, pose_data_array)
            interp_joints = self.interpolate_states(sorted_image_timestamps, sorted_joint_timestamps, joint_data_array)
            interp_end_effectors = self.interpolate_states(sorted_image_timestamps, sorted_end_effector_timestamps, end_effector_data_array)
            
            processed_arm_data[arm_id] = {
                "pose": interp_poses,
                "joint": interp_joints,
                "end_effector": interp_end_effectors
            }
        
        # 创建HDF5文件，符合view_hdf5要求的格式
        with h5py.File(output_file, 'w') as hdf5_file:
            # 创建组
            # episode_group = hdf5_file.create_group("episodes/episode_0")
            obs_group = hdf5_file.create_group("observations")
            image_group = obs_group.create_group("images")  # 符合view_hdf5要求的结构
            state_group = obs_group.create_group("state")
            action_group = hdf5_file.create_group("actions")
            metadata_group = hdf5_file.create_group("metadata")
            info_group = hdf5_file.create_group("info")
            
            # 保存图像数据，符合view_hdf5要求的格式
            # 为每个摄像头创建数据集
            for camera_id in sorted(image_data.keys()):
                # 使用更友好的摄像头名称，符合view_hdf5期望的命名方式
                camera_name = f"cam_{camera_id}" 
                
                # 收集该摄像头的所有图像数据
                image_list = []
                for timestamp in sorted_image_timestamps:
                    if timestamp in image_data[camera_id]:
                        image_path = image_data[camera_id][timestamp]
                        try:
                            # 直接读取图像字节数据，不转换为JPEG格式
                            with open(image_path, 'rb') as f:
                                image_bytes = f.read()
                            print(len(image_bytes))
                            # 确保数据是bytes类型并且不为空
                            if isinstance(image_bytes, bytes) and len(image_bytes) > 0:
                                image_list.append(image_bytes)
                            else:
                                # 添加一个空图像作为占位符
                                image_list.append(b'')
                        except Exception as e:
                            print(f"Error loading image {image_path}: {e}")
                            # 添加一个空图像作为占位符
                            image_list.append(b'')
                    else:
                        # 添加一个空图像作为占位符
                        image_list.append(b'')
                
                try:
                    # 确保数据集中没有重复名称
                    if camera_name in image_group:
                        del image_group[camera_name]
                    
                    # 创建数据集，使用h5py.string_dtype()而不是JPEG格式
                    image_dataset = image_group.create_dataset(
                        camera_name,
                        data=np.array(image_list, dtype=h5py.string_dtype()),
                        compression='gzip'
                    )
                    print(f"Successfully created dataset for camera {camera_name}")
                except Exception as e:
                    print(f"Error creating dataset for camera {camera_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    # 创建一个空的数据集作为后备
                    try:
                        # 确保数据集中没有重复名称
                        if camera_name in image_group:
                            del image_group[camera_name]
                            
                        empty_images = [b'' for _ in range(len(sorted_image_timestamps))]
                        image_dataset = image_group.create_dataset(
                            camera_name,
                            data=np.array(empty_images, dtype=h5py.special_dtype(vlen=bytes)),
                            compression='gzip'
                        )
                        print(f"Created fallback empty dataset for camera {camera_name}")
                    except Exception as e2:
                        print(f"Second attempt failed for camera {camera_name}: {e2}")
                        import traceback
                        traceback.print_exc()
                        try:
                            # 创建最小化的空数据集
                            if camera_name in image_group:
                                del image_group[camera_name]
                                
                            image_dataset = image_group.create_dataset(
                                camera_name,
                                shape=(len(sorted_image_timestamps),),
                                dtype=h5py.special_dtype(vlen=bytes),
                                compression='gzip'
                            )
                            print(f"Created minimal fallback dataset for camera {camera_name}")
                        except Exception as e3:
                            print(f"Third attempt failed for camera {camera_name}: {e3}")
                            # 最后的备选方案
                            if camera_name in image_group:
                                del image_group[camera_name]
            
            # 保存状态数据（观测值）
            # 为每个臂创建子组
            for arm_id in processed_arm_data:
                arm_group = state_group.create_group(f"arm_{arm_id}")
                arm_data = processed_arm_data[arm_id]
                arm_group.create_dataset("pose", data=arm_data["pose"], compression='gzip')
                arm_group.create_dataset("joint", data=arm_data["joint"], compression='gzip')
                arm_group.create_dataset("end_effector", data=arm_data["end_effector"], compression='gzip')
            
            # 保存动作数据（这里简单地使用与观测相同的数据）
            # 为每个臂创建子组
            for arm_id in processed_arm_data:
                arm_group = action_group.create_group(f"arm_{arm_id}")
                arm_data = processed_arm_data[arm_id]
                arm_group.create_dataset("pose", data=arm_data["pose"], compression='gzip')
                arm_group.create_dataset("joint", data=arm_data["joint"], compression='gzip')
                arm_group.create_dataset("end_effector", data=arm_data["end_effector"], compression='gzip')
            
            action_group.create_dataset("timestamps", data=np.array(sorted_image_timestamps), compression='gzip')
            
            # 保存元数据
            def safe_set_attr(group, key, value):
                """
                安全地设置h5py组的属性，处理各种数据类型
                """
                try:
                    if isinstance(value, (dict, list, tuple)):
                        group.attrs[key] = json.dumps(value)
                    elif isinstance(value, (int, float, str, bool)):
                        group.attrs[key] = value
                    elif value is None:
                        group.attrs[key] = "null"
                    else:
                        group.attrs[key] = str(value)
                except Exception as e:
                    print(f"Warning: Could not save attribute '{key}': {e}")
                    group.attrs[key] = "Conversion failed"
            
            # 使用安全的方法设置metadata_group属性
            for key, value in metadata.items():
                safe_set_attr(metadata_group, key, value)
            
            # 使用安全的方法设置info_group属性
            safe_set_attr(info_group, "total_episodes", 1)
            safe_set_attr(info_group, "total_frames", len(sorted_image_timestamps))
            safe_set_attr(info_group, "num_cameras", len(image_data))
            safe_set_attr(info_group, "num_arms", len(processed_arm_data))
            safe_set_attr(info_group, "version", "1.0")
            
        print(f"Saved HDF5 file to {output_file}")
    
    def process_all_sessions(self):
        """
        处理所有会话数据
        """
        sessions = self.find_sessions()
        print(f"Found {len(sessions)} sessions to process")
        
        for session in sessions:
            try:
                self.process_session_to_hdf5(session)
            except Exception as e:
                print(f"Error processing session {session}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Process teleoperation data from temp format to HDF5")
    parser.add_argument("--temp_dir", default="datasets/temp", help="Temporary data directory")
    parser.add_argument("--output_dir", default="datasets/hdf5", help="Output HDF5 directory")
    parser.add_argument("--session", help="Specific session ID to process (default: process all)")
    
    args = parser.parse_args()
    
    processor = DataPostProcessor(args.temp_dir, args.output_dir)
    
    if args.session:
        processor.process_session_to_hdf5(args.session)
    else:
        processor.process_all_sessions()


if __name__ == "__main__":
    main()