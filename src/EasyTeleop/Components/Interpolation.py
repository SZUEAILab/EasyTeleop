import threading
import time
import numpy as np
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from typing import List, Dict, Any, Tuple, Callable

class Interpolation:
    """
    插值组件，用于处理带时间戳的位姿数据并进行插值处理
    位姿数据格式: [x, y, z, rx, ry, rz]
    """
    
    def __init__(self, max_data_points: int = 100, interpolation_rate: float = 0.005):
        """
        初始化插值组件
        
        Args:
            max_data_points: 队列最大数据点数
            interpolation_rate: 插值时间间隔（秒）- 现在是200Hz (0.005s)
        """
        # 使用deque存储带时间戳的数据点，每个元素为 (timestamp, pose_data)
        self.data_queue = deque(maxlen=max_data_points)
        self.interpolated_data = deque(maxlen=max_data_points*5)  # 插值后的数据更多
        
        # 插值参数
        self.interpolation_rate = interpolation_rate  # 插值时间间隔 (200Hz)
        self.delay = 0.1  # 延迟时间 (100ms)
        
        # 线程控制
        self.interpolation_thread = None
        self.visualization_thread = None
        self.running = False
        
        # 可视化相关
        self.fig = None
        self.axs = None
        self.ani = None

        self._events: Dict[str, Callable] = {
            "pose": self._default_callback,
        }
        
    def on(self, event_name: str, callback: Callable = None) -> Callable:
        """
        注册事件回调函数 - 可作为装饰器或普通方法使用
        :param event_name: 事件名称
        :param callback: 回调函数（可选，当作为装饰器使用时不需要）
        :return: 装饰器函数或注册结果
        """
        # 装饰器工厂模式
        def decorator(func):
            if not callable(func):
                raise ValueError("回调函数必须是可调用对象")
                
            # 如果事件存在则更新回调
            if event_name in self._events:
                self._events[event_name] = func
            else:
                # 如果事件不存在，添加新的事件处理器
                self._events[event_name] = func
            return func
        
        # 如果提供了callback参数，则按照原来的方式工作
        if callback is not None:
            return decorator(callback)
        
        # 否则返回装饰器
        return decorator

    def off(self, event_name: str) -> bool:
        """
        移除事件回调函数，恢复默认回调
        :param event_name: 事件名称
        """
        if event_name in self._events:
            self._events[event_name] = self._default_callback
            return True
        
        return False

    def emit(self, event_name: str, *args, **kwargs) -> None:
        """
        触发事件，执行注册的回调函数
        :param event_name: 事件名称
        :param args: 位置参数
        :param kwargs: 关键字参数
        """
        if event_name in self._events:
            try:
                self._events[event_name](*args, **kwargs)
            except Exception as e:
                self.emit("error", f"事件{event_name}执行失败: {str(e)}")

    def _default_callback(self,*args, **kwargs):
        pass
    def add_pose_data(self, pose_data: List[float], timestamp: float = None) -> None:
        """
        添加位姿数据到队列
        
        Args:
            pose_data: 位姿数据 [x, y, z, rx, ry, rz]
            timestamp: 时间戳，如果为None则使用当前时间
        """
        if timestamp is None:
            timestamp = time.time()
            
        # 确保数据格式正确
        if len(pose_data) != 6:
            raise ValueError("Pose data must contain exactly 6 elements: [x, y, z, rx, ry, rz]")
            
        # 将带时间戳的数据添加到队列
        self.data_queue.append((timestamp, pose_data))
        
    def start(self) -> None:
        """
        启动插值线程和可视化
        """
        if self.running:
            return
            
        self.running = True
        
        # 启动插值线程
        self.interpolation_thread = threading.Thread(target=self._interpolation_loop, daemon=True)
        self.interpolation_thread.start()
        
        # 启动可视化线程
        self.visualization_thread = threading.Thread(target=self._visualization_loop, daemon=True)
        self.visualization_thread.start()
        
    def stop(self) -> None:
        """
        停止插值线程和可视化
        """
        self.running = False
        if self.interpolation_thread:
            self.interpolation_thread.join()
        if self.visualization_thread:
            self.visualization_thread.join()
            
        # 停止可视化动画
        if self.ani:
            self.ani.event_source.stop()
            
    def _interpolation_loop(self) -> None:
        """
        插值线程主循环，以固定200Hz频率运行
        使用当前时间减去100ms来匹配左右帧进行插值
        """
        last_interp_time = time.time()
        
        while self.running:
            current_time = time.time()
            target_time = current_time - self.delay  # 目标时间 = 当前时间 - 100ms延迟
            
            # 查找要插值的时间点对应的左右帧
            left_point = None
            right_point = None
            
            # 遍历数据队列找到合适的左右帧
            for i in range(len(self.data_queue) - 1):
                t1, data1 = self.data_queue[i]
                t2, data2 = self.data_queue[i + 1]
                
                # 找到包含target_time的时间区间
                if t1 <= target_time <= t2:
                    left_point = (t1, data1)
                    right_point = (t2, data2)
                    break
            
            # 如果找到了合适的区间，则进行插值
            if left_point and right_point:
                t1, data1 = left_point
                t2, data2 = right_point
                
                # 计算插值比例
                if t2 != t1:
                    ratio = (target_time - t1) / (t2 - t1)
                else:
                    ratio = 0
                
                # 线性插值计算
                interpolated = self._linear_interpolate(data1, data2, ratio)
                
                # 添加插值后的数据
                self.interpolated_data.append((target_time, interpolated))
                self.emit("pose", interpolated)
            
            # 确保以固定频率运行
            elapsed = time.time() - last_interp_time
            sleep_time = max(1e-6, self.interpolation_rate - elapsed)
            time.sleep(sleep_time)
            last_interp_time = time.time()
            
    def _linear_interpolate(self, data1: List[float], data2: List[float], ratio: float) -> List[float]:
        """
        线性插值函数
        
        Args:
            data1: 起始位姿数据 [x, y, z, rx, ry, rz]
            data2: 结束位姿数据 [x, y, z, rx, ry, rz]
            ratio: 插值比例 (0-1)
            
        Returns:
            插值结果 [x, y, z, rx, ry, rz]
        """
        return [d1 + (d2 - d1) * ratio for d1, d2 in zip(data1, data2)]
        
    def _visualization_loop(self) -> None:
        """
        可视化线程主循环
        """
        # 设置matplotlib使用交互式后端
        plt.ion()
        
        # 创建图形和子图 (位置和旋转分开显示)
        self.fig, self.axs = plt.subplots(2, 3, figsize=(15, 8))
        self.fig.suptitle('Original vs Interpolated Pose Data')
        
        # 设置子图标题
        titles = ['X Position', 'Y Position', 'Z Position', 'RX Rotation', 'RY Rotation', 'RZ Rotation']
        labels = ['X', 'Y', 'Z', 'RX', 'RY', 'RZ']
        
        # 初始化线条
        original_lines = []
        interpolated_scatters = []  # 改为存储散点图对象
        
        for i in range(2):  # 2行 (位置和旋转)
            for j in range(3):  # 3列 (X/Y/Z 或 RX/RY/RZ)
                idx = i * 3 + j
                orig_line, = self.axs[i, j].plot([], [], 'ro-', label='Original', markersize=4)
                # 创建空的散点图
                interp_scatter = self.axs[i, j].scatter([], [], c='blue', s=10, label='Interpolated', alpha=0.7)
                
                original_lines.append(orig_line)
                interpolated_scatters.append(interp_scatter)
                
                self.axs[i, j].set_title(titles[idx])
                self.axs[i, j].set_xlabel('Time (s)')
                self.axs[i, j].set_ylabel(f'{labels[idx]} Value')
                self.axs[i, j].legend()
                self.axs[i, j].grid(True)
        
        def update_plot(frame):
            # 为每个子图更新数据
            for idx in range(6):  # 6个维度
                i = idx // 3  # 行索引 (0或1)
                j = idx % 3   # 列索引 (0, 1, 或 2)
                
                # 更新原始数据线条
                if self.data_queue:
                    original_times, original_values = zip(*self.data_queue)
                    original_y = [val[idx] for val in original_values]
                    original_lines[idx].set_data(original_times, original_y)
                
                # 更新插值数据散点
                if self.interpolated_data:
                    interp_times, interp_values = zip(*self.interpolated_data)
                    interp_y = [val[idx] for val in interp_values]
                    # 更新散点图数据
                    offsets = np.column_stack((interp_times, interp_y))
                    interpolated_scatters[idx].set_offsets(offsets)
                
                # 自动调整坐标轴
                all_times = []
                all_values = []
                
                if self.data_queue:
                    times, values = zip(*self.data_queue)
                    all_times.extend(times)
                    all_values.extend([val[idx] for val in values])
                    
                if self.interpolated_data:
                    times, values = zip(*self.interpolated_data)
                    all_times.extend(times)
                    all_values.extend([val[idx] for val in values])
                    
                if all_times and all_values:
                    self.axs[i, j].set_xlim(min(all_times), max(all_times))
                    y_range = max(all_values) - min(all_values)
                    padding = y_range * 0.1 if y_range > 0 else 1
                    self.axs[i, j].set_ylim(min(all_values) - padding, max(all_values) + padding)
            
            # 调整布局
            self.fig.tight_layout()
            
            # 返回更新的对象
            return original_lines + interpolated_scatters
        
        # 创建动画
        self.ani = FuncAnimation(
            self.fig, 
            update_plot, 
            blit=False, 
            interval=100,  # 更新频率
            cache_frame_data=False
        )
        
        plt.show()
        
        # 保持图形窗口开启
        while self.running:
            plt.pause(0.1)
            
        plt.ioff()

# 使用示例
if __name__ == "__main__":
    # 创建插值组件实例
    interpolator = Interpolation(max_data_points=50, interpolation_rate=0.005)
    
    # 启动组件
    interpolator.start()
    
    # 模拟添加数据
    for i in range(30):
        # 生成一些测试数据 [x, y, z, rx, ry, rz]
        test_data = [
            np.sin(i/5.0) * 100,    # X坐标
            np.cos(i/5.0) * 100,    # Y坐标
            i * 2,                  # Z坐标
            np.sin(i/3.0) * 45,     # RX角度
            np.cos(i/3.0) * 45,     # RY角度
            i * 1.5                 # RZ角度
        ]
        interpolator.add_pose_data(test_data)
        time.sleep(0.016)  # 模拟约60Hz的数据到达间隔
        
    # 运行一段时间后停止
    time.sleep(5)
    interpolator.stop()