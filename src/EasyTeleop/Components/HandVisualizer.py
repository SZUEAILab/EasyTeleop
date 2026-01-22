import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from matplotlib.animation import FuncAnimation
from queue import Queue
import matplotlib
import threading
import time
# matplotlib.use('TkAgg')  # 使用TkAgg后端

class HandVisualizer:
    # OpenXR手部关节定义
    XR_HAND_JOINT_PALM_EXT = 0
    XR_HAND_JOINT_WRIST_EXT = 1
    XR_HAND_JOINT_THUMB_METACARPAL_EXT = 2
    XR_HAND_JOINT_THUMB_PROXIMAL_EXT = 3
    XR_HAND_JOINT_THUMB_DISTAL_EXT = 4
    XR_HAND_JOINT_THUMB_TIP_EXT = 5
    XR_HAND_JOINT_INDEX_METACARPAL_EXT = 6
    XR_HAND_JOINT_INDEX_PROXIMAL_EXT = 7
    XR_HAND_JOINT_INDEX_INTERMEDIATE_EXT = 8
    XR_HAND_JOINT_INDEX_DISTAL_EXT = 9
    XR_HAND_JOINT_INDEX_TIP_EXT = 10
    XR_HAND_JOINT_MIDDLE_METACARPAL_EXT = 11
    XR_HAND_JOINT_MIDDLE_PROXIMAL_EXT = 12
    XR_HAND_JOINT_MIDDLE_INTERMEDIATE_EXT = 13
    XR_HAND_JOINT_MIDDLE_DISTAL_EXT = 14
    XR_HAND_JOINT_MIDDLE_TIP_EXT = 15
    XR_HAND_JOINT_RING_METACARPAL_EXT = 16
    XR_HAND_JOINT_RING_PROXIMAL_EXT = 17
    XR_HAND_JOINT_RING_INTERMEDIATE_EXT = 18
    XR_HAND_JOINT_RING_DISTAL_EXT = 19
    XR_HAND_JOINT_RING_TIP_EXT = 20
    XR_HAND_JOINT_LITTLE_METACARPAL_EXT = 21
    XR_HAND_JOINT_LITTLE_PROXIMAL_EXT = 22
    XR_HAND_JOINT_LITTLE_INTERMEDIATE_EXT = 23
    XR_HAND_JOINT_LITTLE_DISTAL_EXT = 24
    XR_HAND_JOINT_LITTLE_TIP_EXT = 25
    
    # 手部连接关系，用于绘制连线
    HAND_CONNECTIONS = [
        # 手掌到手腕
        (XR_HAND_JOINT_PALM_EXT, XR_HAND_JOINT_WRIST_EXT),
        
        # 拇指
        (XR_HAND_JOINT_WRIST_EXT, XR_HAND_JOINT_THUMB_METACARPAL_EXT),
        (XR_HAND_JOINT_THUMB_METACARPAL_EXT, XR_HAND_JOINT_THUMB_PROXIMAL_EXT),
        (XR_HAND_JOINT_THUMB_PROXIMAL_EXT, XR_HAND_JOINT_THUMB_DISTAL_EXT),
        (XR_HAND_JOINT_THUMB_DISTAL_EXT, XR_HAND_JOINT_THUMB_TIP_EXT),
        
        # 食指
        (XR_HAND_JOINT_WRIST_EXT, XR_HAND_JOINT_INDEX_METACARPAL_EXT),
        (XR_HAND_JOINT_INDEX_METACARPAL_EXT, XR_HAND_JOINT_INDEX_PROXIMAL_EXT),
        (XR_HAND_JOINT_INDEX_PROXIMAL_EXT, XR_HAND_JOINT_INDEX_INTERMEDIATE_EXT),
        (XR_HAND_JOINT_INDEX_INTERMEDIATE_EXT, XR_HAND_JOINT_INDEX_DISTAL_EXT),
        (XR_HAND_JOINT_INDEX_DISTAL_EXT, XR_HAND_JOINT_INDEX_TIP_EXT),
        
        # 中指
        (XR_HAND_JOINT_WRIST_EXT, XR_HAND_JOINT_MIDDLE_METACARPAL_EXT),
        (XR_HAND_JOINT_MIDDLE_METACARPAL_EXT, XR_HAND_JOINT_MIDDLE_PROXIMAL_EXT),
        (XR_HAND_JOINT_MIDDLE_PROXIMAL_EXT, XR_HAND_JOINT_MIDDLE_INTERMEDIATE_EXT),
        (XR_HAND_JOINT_MIDDLE_INTERMEDIATE_EXT, XR_HAND_JOINT_MIDDLE_DISTAL_EXT),
        (XR_HAND_JOINT_MIDDLE_DISTAL_EXT, XR_HAND_JOINT_MIDDLE_TIP_EXT),
        
        # 无名指
        (XR_HAND_JOINT_WRIST_EXT, XR_HAND_JOINT_RING_METACARPAL_EXT),
        (XR_HAND_JOINT_RING_METACARPAL_EXT, XR_HAND_JOINT_RING_PROXIMAL_EXT),
        (XR_HAND_JOINT_RING_PROXIMAL_EXT, XR_HAND_JOINT_RING_INTERMEDIATE_EXT),
        (XR_HAND_JOINT_RING_INTERMEDIATE_EXT, XR_HAND_JOINT_RING_DISTAL_EXT),
        (XR_HAND_JOINT_RING_DISTAL_EXT, XR_HAND_JOINT_RING_TIP_EXT),
        
        # 小指
        (XR_HAND_JOINT_WRIST_EXT, XR_HAND_JOINT_LITTLE_METACARPAL_EXT),
        (XR_HAND_JOINT_LITTLE_METACARPAL_EXT, XR_HAND_JOINT_LITTLE_PROXIMAL_EXT),
        (XR_HAND_JOINT_LITTLE_PROXIMAL_EXT, XR_HAND_JOINT_LITTLE_INTERMEDIATE_EXT),
        (XR_HAND_JOINT_LITTLE_INTERMEDIATE_EXT, XR_HAND_JOINT_LITTLE_DISTAL_EXT),
        (XR_HAND_JOINT_LITTLE_DISTAL_EXT, XR_HAND_JOINT_LITTLE_TIP_EXT),
    ]
    
    def __init__(self):
        self.data_queue = Queue()
        self.left_joints_data = None
        self.right_joints_data = None
        self.left_root_pose = None
        self.right_root_pose = None
        self.running = False
        
        # 初始化图形相关变量
        self.fig = None
        self.ax = None
        self.left_joints_scatter = None
        self.right_joints_scatter = None
        self.left_bone_lines = []
        self.right_bone_lines = []

    def initialize_plot(self):
        """初始化绘图组件"""
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # 设置图表属性
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_xlim([-0.12, 0.12])
        self.ax.set_ylim([-0.12, 0.12])
        self.ax.set_zlim([-0.12, 0.12])
        self.ax.set_title('Hand Joints Visualization (Relative to rootPose)')
        
        # 创建散点图用于显示关节
        self.left_joints_scatter = self.ax.scatter([], [], [], c='red', marker='o', s=30, label='Left Hand')
        self.right_joints_scatter = self.ax.scatter([], [], [], c='blue', marker='o', s=30, label='Right Hand')
        self.ax.legend()

        # 创建连线用于显示手指骨骼
        self.left_bone_lines = []
        self.right_bone_lines = []
        for _ in self.HAND_CONNECTIONS:
            left_line, = self.ax.plot([], [], [], 'r-', linewidth=1.5, alpha=0.7)
            right_line, = self.ax.plot([], [], [], 'b-', linewidth=1.5, alpha=0.7)
            self.left_bone_lines.append(left_line)
            self.right_bone_lines.append(right_line)

    def quaternion_to_rotation_matrix(self, q):
        """四元数转旋转矩阵，q为dict或list[x, y, z, w]"""
        if isinstance(q, dict):
            x, y, z, w = q['x'], q['y'], q['z'], q['w']
        else:
            x, y, z, w = q
        # 四元数归一化
        norm = np.sqrt(x*x + y*y + z*z + w*w)
        if norm > 0:
            x, y, z, w = x/norm, y/norm, z/norm, w/norm
        R = np.array([
            [1-2*(y**2+z**2), 2*(x*y-z*w),   2*(x*z+y*w)],
            [2*(x*y+z*w),     1-2*(x**2+z**2), 2*(y*z-x*w)],
            [2*(x*z-y*w),     2*(y*z+x*w),   1-2*(x**2+y**2)]
        ])
        return R

    def transform_to_root_pose(self, positions, root_pose):
        """将关节位置转换为相对于rootPose的坐标"""
        if root_pose is None:
            return positions
            
        # 获取根姿势的位置和旋转
        root_pos = np.array([root_pose['position']['x'], 
                            root_pose['position']['y'], 
                            root_pose['position']['z']])
        
        root_rot = self.quaternion_to_rotation_matrix(root_pose['rotation'])
        
        # 变换所有关节位置
        transformed_positions = []
        for pos in positions:
            # 相对于根姿势的位置
            relative_pos = pos - root_pos
            # 应用根姿势的旋转逆变换
            transformed_pos = np.dot(np.linalg.inv(root_rot), relative_pos)
            transformed_positions.append(transformed_pos)
            
        return np.array(transformed_positions)

    def extract_positions(self, joints):
        """从关节数据中提取位置信息"""
        positions = []
        for joint in joints:
            pos = joint['position']
            positions.append([pos['x'], pos['y'], pos['z']])
        return np.array(positions)

    def update_bones(self, positions, bone_lines, color='r'):
        """更新手指骨骼连线"""
        if positions is None or len(positions) < 26:
            return
            
        for i, (start_idx, end_idx) in enumerate(self.HAND_CONNECTIONS):
            if i < len(bone_lines):
                start_pos = positions[start_idx]
                end_pos = positions[end_idx]
                bone_lines[i].set_data([start_pos[0], end_pos[0]], 
                                      [start_pos[1], end_pos[1]])
                bone_lines[i].set_3d_properties([start_pos[2], end_pos[2]])

    def update(self, frame):
        """动画更新函数"""
        # 处理队列中的数据
        while not self.data_queue.empty():
            data = self.data_queue.get()
            
            # 处理左手数据
            if 'leftHand' in data and data['leftHand']['isTracked'] and 'joints' in data['leftHand']:
                self.left_joints_data = data['leftHand']['joints']
                self.left_root_pose = data['leftHand'].get('rootPose', None)
            else:
                self.left_joints_data = None
                
            # 处理右手数据
            if 'rightHand' in data and data['rightHand']['isTracked'] and 'joints' in data['rightHand']:
                self.right_joints_data = data['rightHand']['joints']
                self.right_root_pose = data['rightHand'].get('rootPose', None)
            else:
                self.right_joints_data = None
        
        # 更新左手
        
        if self.left_joints_data and len(self.left_joints_data) >= 26:
            positions = self.extract_positions(self.left_joints_data)
            
            # 转换为相对于rootPose的坐标
            # positions = self.transform_to_root_pose(positions, self.root_pose)
            positions = positions - np.array([self.left_root_pose['position']['x'],self.left_root_pose['position']['y'],self.left_root_pose['position']['z']]) 
            
            # 更新关节散点
            xs = positions[:, 0]
            ys = positions[:, 1]
            zs = positions[:, 2]
            self.left_joints_scatter._offsets3d = (xs, ys, zs)
            
            # 更新骨骼连线
            self.update_bones(positions, self.left_bone_lines, 'r')
            
        # 更新右手
        if self.right_joints_data and len(self.right_joints_data) >= 26:
            positions = self.extract_positions(self.right_joints_data)
            
            # 转换为相对于rootPose的坐标
            positions = positions - np.array([self.right_root_pose['position']['x'],self.right_root_pose['position']['y'],self.right_root_pose['position']['z']]) 
            
            # 更新关节散点
            xs = positions[:, 0]
            ys = positions[:, 1]
            zs = positions[:, 2]
            self.right_joints_scatter._offsets3d = (xs, ys, zs)
            
            # 更新骨骼连线
            self.update_bones(positions, self.right_bone_lines, 'b')
            
        return [self.left_joints_scatter, self.right_joints_scatter] + self.left_bone_lines + self.right_bone_lines

    def add_data(self, data):
        """添加新的手部数据"""
        self.data_queue.put(data)

    def start(self):
        """开始动画显示"""
        self.initialize_plot()
        self.running = True
        self.ani = FuncAnimation(self.fig, self.update, interval=50, 
                                save_count=50, blit=False)
        plt.show()

    def stop(self):
        """停止显示"""
        self.running = False
        if self.fig:
            plt.close(self.fig)