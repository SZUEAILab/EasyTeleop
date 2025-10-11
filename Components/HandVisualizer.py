import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from matplotlib.animation import FuncAnimation
from queue import Queue
import matplotlib
matplotlib.use('TkAgg')  # 使用TkAgg后端

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
        (XR_HAND_JOINT_PALM_EXT, XR_HAND_JOINT_THUMB_METACARPAL_EXT),
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
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.data_queue = Queue()
        self.joints_data = None
        self.running = True
        
        # 设置图表属性
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_xlim([-0.5, 0.5])
        self.ax.set_ylim([-0.5, 0.5])
        self.ax.set_zlim([-0.5, 0.5])
        self.ax.set_title('Left Hand Joints Visualization')
        
        # 创建散点图用于显示关节
        self.joints_scatter = self.ax.scatter([], [], [], c='red', marker='o', s=30)
        
        # 创建连线用于显示手指骨骼
        self.bone_lines = []
        for _ in self.HAND_CONNECTIONS:
            line, = self.ax.plot([], [], [], 'b-', linewidth=1.5)
            self.bone_lines.append(line)

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

    def extract_positions(self, joints):
        """从关节数据中提取位置信息"""
        positions = []
        for joint in joints:
            pos = joint['position']
            positions.append([pos['x'], pos['y'], pos['z']])
        return np.array(positions)

    def update_bones(self, positions):
        """更新手指骨骼连线"""
        if positions is None or len(positions) < 26:
            return
            
        for i, (start_idx, end_idx) in enumerate(self.HAND_CONNECTIONS):
            if i < len(self.bone_lines):
                start_pos = positions[start_idx]
                end_pos = positions[end_idx]
                self.bone_lines[i].set_data([start_pos[0], end_pos[0]], 
                                          [start_pos[1], end_pos[1]])
                self.bone_lines[i].set_3d_properties([start_pos[2], end_pos[2]])

    def update(self, frame):
        """动画更新函数"""
        # 处理队列中的数据
        while not self.data_queue.empty():
            data = self.data_queue.get()
            if 'leftHand' in data and data['leftHand']['isTracked'] and 'joints' in data['leftHand']:
                self.joints_data = data['leftHand']['joints']
        
        if self.joints_data:
            print(len(self.joints_data))

        
        if self.joints_data and len(self.joints_data) >= 26:
            positions = self.extract_positions(self.joints_data)
            
            # 更新关节散点
            xs = positions[:, 0]
            ys = positions[:, 1]
            zs = positions[:, 2]
            self.joints_scatter._offsets3d = (xs, ys, zs)
            
            # 更新骨骼连线
            self.update_bones(positions)
            
        return [self.joints_scatter] + self.bone_lines

    def add_data(self, data):
        """添加新的手部数据"""
        self.data_queue.put(data)

    def start(self):
        """开始动画显示"""
        ani = FuncAnimation(self.fig, self.update, interval=50, 
                          save_count=50, blit=False)
        plt.show()

    def stop(self):
        """停止显示"""
        self.running = False
        plt.close('all')