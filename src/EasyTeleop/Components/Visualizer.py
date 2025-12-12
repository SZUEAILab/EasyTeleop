import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from matplotlib.animation import FuncAnimation
import json
from queue import Queue
import threading
import matplotlib
# matplotlib.use('TkAgg')  # 使用TkAgg后端

class Visualizer:
    def __init__(self):
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        # 将原来的data_queue分成左手和右手两个队列
        self.left_data_queue = Queue()
        self.right_data_queue = Queue()
        self.left_pos = np.array([0, 0, 0])
        self.right_pos = np.array([0, 0, 0])
        self.left_rot = np.array([0, 0, 0])  # 欧拉角 [x,y,z]
        self.right_rot = np.array([0, 0, 0])
        self.running = True
        
        # 设置图表属性
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.set_xlim([-1, 1])
        self.ax.set_ylim([-1, 1])
        self.ax.set_zlim([-1, 1])
        
        # 创建散点
        self.left_point = self.ax.scatter([], [], [], c='red', marker='o', s=100, label='Left Controller')
        self.right_point = self.ax.scatter([], [], [], c='blue', marker='o', s=100, label='Right Controller')
        self.ax.legend()

        # 添加坐标轴线
        self.axis_length = 0.5
        self.left_axes = [self.ax.plot([], [], [], 'r-', linewidth=2)[0],  # X轴
                         self.ax.plot([], [], [], 'g-', linewidth=2)[0],  # Y轴
                         self.ax.plot([], [], [], 'b-', linewidth=2)[0]]  # Z轴
        self.right_axes = [self.ax.plot([], [], [], 'r-', linewidth=2)[0],
                          self.ax.plot([], [], [], 'g-', linewidth=2)[0],
                          self.ax.plot([], [], [], 'b-', linewidth=2)[0]]

    def euler_to_rotation_matrix(self, euler_angles):
        """欧拉角转换为旋转矩阵 (按照XYZ顺序)"""
        x, y, z = np.radians(euler_angles)
        
        # X旋转
        Rx = np.array([[1, 0, 0],
                       [0, np.cos(x), -np.sin(x)],
                       [0, np.sin(x), np.cos(x)]])
        
        # Y旋转
        Ry = np.array([[np.cos(y), 0, np.sin(y)],
                       [0, 1, 0],
                       [-np.sin(y), 0, np.cos(y)]])
        
        # Z旋转
        Rz = np.array([[np.cos(z), -np.sin(z), 0],
                       [np.sin(z), np.cos(z), 0],
                       [0, 0, 1]])
        
        # 组合旋转
        R = Rz @ Ry @ Rx
        return R

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

    def update_axes(self, pos, rot, axes, is_quat=False):
        """更新坐标轴的位置和方向，is_quat=True时rot为四元数"""
        if is_quat:
            R = self.quaternion_to_rotation_matrix(rot)
        else:
            R = self.euler_to_rotation_matrix(rot)
        basis = np.eye(3) * self.axis_length
        rotated_basis = np.dot(R, basis.T).T
        for i, axis in enumerate(axes):
            start = pos
            end = pos + rotated_basis[i]
            axis.set_data([start[0], end[0]], [start[1], end[1]])
            axis.set_3d_properties([start[2], end[2]])

    def is_quaternion(self, rotation_data):
        """判断是四元数还是欧拉角"""
        if isinstance(rotation_data, dict):
            # 如果包含'w'键，则认为是四元数
            return 'w' in rotation_data
        elif isinstance(rotation_data, (list, tuple)) and len(rotation_data) == 4:
            # 如果是长度为4的列表或元组，则认为是四元数
            return True
        else:
            # 否则认为是欧拉角
            return False

    def update(self, frame):
        # 处理左手队列数据
        while not self.left_data_queue.empty():
            data = self.left_data_queue.get()
            self.left_pos = np.array([data['position']['x'], data['position']['y'], data['position']['z']])
            # 判断是否为四元数
            self.left_is_quat = self.is_quaternion(data['rotation'])
            self.left_rot = data['rotation']

        # 处理右手队列数据
        while not self.right_data_queue.empty():
            data = self.right_data_queue.get()
            self.right_pos = np.array([data['position']['x'], data['position']['y'], data['position']['z']])
            # 判断是否为四元数
            self.right_is_quat = self.is_quaternion(data['rotation'])
            self.right_rot = data['rotation']

        # 更新控制器位置
        self.left_point._offsets3d = (self.left_pos[0:1], self.left_pos[1:2], self.left_pos[2:3])
        self.right_point._offsets3d = (self.right_pos[0:1], self.right_pos[1:2], self.right_pos[2:3])

        # 更新方向轴
        self.update_axes(self.left_pos, self.left_rot, self.left_axes, getattr(self, 'left_is_quat', False))
        self.update_axes(self.right_pos, self.right_rot, self.right_axes, getattr(self, 'right_is_quat', False))

        return self.left_point, self.right_point

    def add_left_data(self, data):
        self.left_data_queue.put(data)

    def add_right_data(self, data):
        self.right_data_queue.put(data)

    def start(self):
        ani = FuncAnimation(self.fig, self.update, interval=50, 
                          save_count=100,  # 限制缓存帧数
                          cache_frame_data=False)  # 禁用帧数据缓存
        plt.show()

    def stop(self):
        self.running = False
        plt.close('all')