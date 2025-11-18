from flask import Flask, render_template, jsonify, request, send_file
import os
import h5py
import numpy as np
import cv2
import base64
import io
from PIL import Image
import json
import subprocess # New import
import atexit     # New import
import signal     # New import


app = Flask(__name__)

# --- RDT Process Management ---
rdt_process = None

def cleanup_rdt_process():
    """Ensure the RDT subprocess is terminated when the main app exits."""
    global rdt_process
    if rdt_process:
        print("Terminating RDT server process...")
        # Use os.killpg to kill the process and its children
        os.killpg(os.getpgid(rdt_process.pid), signal.SIGTERM)
        rdt_process = None
        print("RDT server process terminated.")

atexit.register(cleanup_rdt_process)
# --- End RDT Process Management ---

def get_database_folders():
    """获取database目录下的所有子文件夹"""
    database_dir = os.path.join(os.getcwd(), 'databases')
    folders = []
    
    if os.path.exists(database_dir) and os.path.isdir(database_dir):
        for item in os.listdir(database_dir):
            item_path = os.path.join(database_dir, item)
            if os.path.isdir(item_path):
                hdf5_count = count_hdf5_files(item_path)
                folders.append({
                    'name': item,
                    'path': item_path,
                    'type': 'subfolder',
                    'hdf5_count': hdf5_count
                })
    return folders

def count_hdf5_files(directory_path):
    """统计指定目录下的HDF5文件数量"""
    count = 0
    try:
        for file in os.listdir(directory_path):
            if file.endswith('.hdf5'):
                count += 1
    except:
        pass
    return count

def get_hdf5_files_from_database_folder(folder_name):
    """获取database下指定文件夹内的所有HDF5文件"""
    database_dir = os.path.join(os.getcwd(), 'databases')
    folder_path = os.path.join(database_dir, folder_name)
    hdf5_files = []
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        try:
            for file in os.listdir(folder_path):
                if file.endswith('.hdf5'):
                    file_path = os.path.join(folder_path, file)
                    file_size = os.path.getsize(file_path)
                    hdf5_files.append({
                        'name': file,
                        'path': file_path,
                        'size': f"{file_size / 1024 / 1024:.2f} MB",
                        'folder': folder_name
                    })
        except Exception as e:
            print(f"Error reading folder {folder_path}: {e}")
    return hdf5_files


def extract_images_from_hdf5(file_path):
    """
    从HDF5文件中按摄像头分组提取图像数据，并转换为base64编码。
    返回一个以摄像头名称为键，图像帧列表为值的字典。
    """
    camera_images = {}
    total_frames = 0
    try:
        with h5py.File(file_path, 'r') as f:
            # 检查是否存在我们期望的数据结构
            if 'observations' in f and 'images' in f['observations']:
                image_group = f['observations']['images']
                # 遍历每个摄像头的数据集 (例如 'cam_wrist', 'cam_right_high')
                for cam_name in image_group.keys():
                    camera_images[cam_name] = []
                    img_data = image_group[cam_name][:]
                    
                    # 记录帧数，我们假设所有摄像头的帧数相同
                    if total_frames == 0:
                        total_frames = len(img_data)

                    for i, img_bytes in enumerate(img_data):
                        # 处理图像数据
                        if isinstance(img_bytes, np.bytes_):
                            img_bytes = img_bytes.item()
                        
                        nparr = np.frombuffer(img_bytes, np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if img is not None:
                            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            pil_img = Image.fromarray(img_rgb)
                            buffer = io.BytesIO()
                            pil_img.save(buffer, format='JPEG', quality=85)
                            img_base64 = base64.b64encode(buffer.getvalue()).decode()
                            camera_images[cam_name].append({
                                'index': i,
                                'data': f"data:image/jpeg;base64,{img_base64}",
                            })
            # 如果没有找到标准结构，尝试其他可能的结构
            elif 'images' in f:
                # 直接在根images组中查找
                image_group = f['images']
                for cam_name in image_group.keys():
                    camera_images[cam_name] = []
                    img_data = image_group[cam_name][:]
                    
                    if total_frames == 0:
                        total_frames = len(img_data)

                    for i, img_bytes in enumerate(img_data):
                        if isinstance(img_bytes, np.bytes_):
                            img_bytes = img_bytes.item()
                            
                        nparr = np.frombuffer(img_bytes, np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if img is not None:
                            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            pil_img = Image.fromarray(img_rgb)
                            buffer = io.BytesIO()
                            pil_img.save(buffer, format='JPEG', quality=85)
                            img_base64 = base64.b64encode(buffer.getvalue()).decode()
                            camera_images[cam_name].append({
                                'index': i,
                                'data': f"data:image/jpeg;base64,{img_base64}",
                            })
    except Exception as e:
        print(f"Error processing HDF5 file: {e}")
    # 注意返回值的变化
    return camera_images, total_frames

@app.route('/')
def index():
    """主页面"""
    return render_template('front_end.html')

@app.route('/api/database_folders')
def get_database_folders_api():
    """获取database目录下的文件夹列表的API"""
    folders = get_database_folders()
    return jsonify(folders)

from flask import send_from_directory

@app.route('/materials/<path:filename>')
def materials_files(filename):
	return send_from_directory(os.path.join(app.root_path, 'materials'), filename)

@app.route('/api/database_files/<folder_name>')
def get_database_files(folder_name):
    """获取database下指定文件夹内的HDF5文件的API"""
    files = get_hdf5_files_from_database_folder(folder_name)
    return jsonify(files)

# This function is not used by the new UI flow, but kept for potential future use
def get_directories():
    """获取当前目录下的所有子目录"""
    # This function seems unused by the provided front-end logic, but we keep it.
    current_dir = os.getcwd()
    directories = [{'name': '当前目录', 'path': current_dir, 'type': 'current'}]
    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)
        if os.path.isdir(item_path):
            directories.append({'name': item, 'path': item_path, 'type': 'subdir'})
    return directories

@app.route('/api/process_hdf5', methods=['POST'])
def process_hdf5():
    """处理HDF5文件并按摄像头分组返回图像数据"""
    data = request.get_json()
    file_path = data.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    # 获取新的数据结构
    camera_images, total_frames = extract_images_from_hdf5(file_path)
    
    # 在返回的JSON中包含新的数据结构
    return jsonify({
        'success': True, 
        'camera_images': camera_images, 
        'total_frames': total_frames,
        'camera_names': list(camera_images.keys()) # 同时返回摄像头名称列表
    })

# ... 文件的其余部分 (包括 start_rdt_server) 保持不变 ...

# --- NEW API Endpoints for RDT Server ---

# 文件路径: utils/Intergrated_interface_system/view_hdf5.py

@app.route('/api/start_rdt_server', methods=['POST'])
def start_rdt_server():
    """
    完全模拟 inference_ym.sh 的行为来启动RDT服务。
    使用正确的相对路径和工作目录。
    """
    global rdt_process
    
    if rdt_process and rdt_process.poll() is None:
        return jsonify({'status': 'already_running', 'message': 'RDT服务已经在运行中。'})

    try:
        # 动态计算项目根目录，这对于使用相对路径至关重要
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
        
        # RDT_server_stream.py 的完整路径
        script_full_path = os.path.join(current_dir, 'RDT_server_stream.py')

        # --- 从您的 inference_ym.sh 文件中提取的正确配置 ---
        model_path_relative = "checkpoints/rdt-hans-V2/checkpoint-10000"
        lang_embeddings_path_relative = "outs/Gripper_Placement_on_Material_Tray.pt"
        ctrl_freq_val = "25"
        # ---------------------------------------------------

        # 验证路径在项目根目录下是否存在 (可选但推荐的安全检查)
        if not os.path.exists(os.path.join(project_root, model_path_relative)):
             error_msg = f"启动失败: 在项目根目录下找不到模型路径: {model_path_relative}"
             return jsonify({'status': 'error', 'message': error_msg}), 400
        if not os.path.exists(os.path.join(project_root, lang_embeddings_path_relative)):
             error_msg = f"启动失败: 在项目根目录下找不到语言嵌入路径: {lang_embeddings_path_relative}"
             return jsonify({'status': 'error', 'message': error_msg}), 400

        # 构建与 inference_ym.sh 完全一致的命令
        command = [
            'python', 
            script_full_path,
            '--pretrained_model_name_or_path', model_path_relative,
            '--lang_embeddings_path', lang_embeddings_path_relative,
            '--ctrl_freq', ctrl_freq_val
        ]
        
        # 关键：设置工作目录为项目根目录，让相对路径生效
        rdt_process = subprocess.Popen(
            command, 
            preexec_fn=os.setsid,
            cwd=project_root
        )
        
        print(f"Successfully started RDT server with command: {' '.join(command)}")
        return jsonify({'status': 'started', 'message': 'RDT服务已根据您的配置成功启动。'})
        
    except Exception as e:
        print(f"Failed to start RDT server: {e}")
        return jsonify({'status': 'error', 'message': f'启动失败: {e}'}), 500

@app.route('/api/stop_rdt_server', methods=['POST'])
def stop_rdt_server():
    """Stops the running RDT server subprocess."""
    global rdt_process
    if not rdt_process or rdt_process.poll() is not None:
        rdt_process = None
        return jsonify({'status': 'not_running', 'message': 'RDT服务未在运行。'})
        
    try:
        print(f"Stopping RDT server with PID: {rdt_process.pid}")
        # Kill the entire process group started with setsid
        os.killpg(os.getpgid(rdt_process.pid), signal.SIGTERM)
        rdt_process.wait() # Wait for the process to terminate
        rdt_process = None
        return jsonify({'status': 'stopped', 'message': 'RDT服务已成功终止。'})
    except Exception as e:
        print(f"Error stopping RDT server: {e}")
        return jsonify({'status': 'error', 'message': f'终止失败: {e}'}), 500

# --- End of NEW API Endpoints ---

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)