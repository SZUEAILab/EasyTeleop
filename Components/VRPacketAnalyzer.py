import matplotlib.pyplot as plt
import numpy as np
from collections import deque
import time
from matplotlib.animation import FuncAnimation
import json
import threading


class VRPacketAnalyzer:
    """
    VR数据包分析器，用于可视化VR数据包的帧率和帧间间隔
    """
    
    def __init__(self, max_points=1000):
        """
        初始化VR数据包分析器
        
        Args:
            max_points: 最大显示数据点数
        """
        self.max_points = max_points
        self.timestamps = deque(maxlen=max_points)
        self.intervals = deque(maxlen=max_points)
        self.framerates = deque(maxlen=max_points)
        
        # 上一个数据包的时间戳
        self.last_timestamp = None
        
        # 初始化图形相关变量
        self.fig = None
        self.ax1 = None
        self.ax2 = None
        self.interval_line = None
        self.framerate_line = None
        self.avg_interval_line = None
        self.avg_framerate_line = None
        
        # 用于存储动画对象
        self.ani = None
        
        # 线程相关
        self.is_running = False
        self.visualization_thread = None
        
        
        
    def add_packet(self, packet):
        """
        添加一个新的VR数据包
        
        Args:
            packet: VR数据包，可以是dict或者JSON字符串
        """
        # 解析数据包
        if isinstance(packet, str):
            try:
                packet = json.loads(packet)
            except json.JSONDecodeError:
                # 如果不是有效的JSON，尝试获取时间戳
                timestamp = time.time()
            else:
                # 从数据包中提取时间戳
                timestamp = packet.get('timestamp', time.time())
        elif isinstance(packet, dict):
            timestamp = packet.get('timestamp', time.time())
        else:
            timestamp = time.time()
        
        # 记录时间戳
        self.timestamps.append(timestamp)
        
        # 计算帧间间隔
        if self.last_timestamp is not None:
            interval = (timestamp - self.last_timestamp) * 1000  # 转换为毫秒
            self.intervals.append(interval)
            
            # 计算帧率 (FPS)
            if interval > 0:
                framerate = 1000.0 / interval
                self.framerates.append(framerate)
            else:
                self.framerates.append(0)
        else:
            # 第一个数据包，没有间隔
            self.intervals.append(0)
            self.framerates.append(0)
        
        self.last_timestamp = timestamp
    
    
    
    def _visualization_loop(self):
        """
        可视化线程主循环
        """
        # 初始化图形
        plt.ion()
        
        # 创建图形和子图
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 8))
        self.fig.suptitle('VR Packet Analysis')
        
        # 设置图表属性
        self.ax1.set_xlabel('Time (s)')
        self.ax1.set_ylabel('Frame Interval (ms)')
        self.ax1.set_title('Frame Intervals Over Time')
        self.ax1.grid(True)
        
        self.ax2.set_xlabel('Time (s)')
        self.ax2.set_ylabel('Framerate (FPS)')
        self.ax2.set_title('Framerate Over Time')
        self.ax2.grid(True)
        
        # 初始化线条
        self.interval_line, = self.ax1.plot([], [], 'b-', linewidth=1, label='Interval')
        self.framerate_line, = self.ax2.plot([], [], 'r-', linewidth=1, label='Framerate')
        
        # 添加平均值线
        self.avg_interval_line = self.ax1.axhline(y=0, color='g', linestyle='--', linewidth=1, label='Average')
        self.avg_framerate_line = self.ax2.axhline(y=0, color='g', linestyle='--', linewidth=1, label='Average')
        
        self.ax1.legend()
        self.ax2.legend()

        def update_plots(frame):
            """
            更新图表
            
            Args:
                frame: 动画帧号
            """
            if len(self.timestamps) == 0:
                return [self.interval_line, self.framerate_line]
            
            # 计算相对于第一个时间戳的时间（秒）
            base_time = self.timestamps[0]
            times = [t - base_time for t in self.timestamps]
            
            # 确保所有数据列表长度一致
            min_length = min(len(times), len(self.intervals), len(self.framerates))
            
            # 更新帧间隔图
            if min_length > 0:
                x_data = times[:min_length]
                y_data = list(self.intervals)[:min_length]
                self.interval_line.set_data(x_data, y_data)
                self.ax1.relim()
                self.ax1.autoscale_view()
                
                # 更新平均间隔线
                if len(self.intervals) > 0:
                    avg_interval = np.mean(list(self.intervals))
                    self.avg_interval_line.set_ydata([avg_interval, avg_interval])
                
            # 更新帧率图
            if min_length > 0:
                x_data = times[:min_length]
                y_data = list(self.framerates)[:min_length]
                self.framerate_line.set_data(x_data, y_data)
                self.ax2.relim()
                self.ax2.autoscale_view()
                
                # 更新平均帧率线
                if len(self.framerates) > 0:
                    avg_framerate = np.mean(list(self.framerates))
                    self.avg_framerate_line.set_ydata([avg_framerate, avg_framerate])
            
            return [self.interval_line, self.framerate_line, self.avg_interval_line, self.avg_framerate_line]
        
        # 创建动画
        self.ani = FuncAnimation(
            self.fig, 
            update_plots, 
            blit=False,
            interval=100,  # 更新间隔（毫秒）
            cache_frame_data=False  # 不缓存帧数据
        )
        
        plt.tight_layout()
        plt.show()
        
        # 保持图形窗口开启
        while self.is_running:
            plt.pause(0.1)
            
        plt.ioff()
        
    def start(self, interval=100):
        """
        开始实时可视化（在独立线程中运行）
        
        Args:
            interval: 更新间隔（毫秒）
        """
        if self.is_running:
            return
            
        self.is_running = True
        # 在独立线程中启动可视化
        self.visualization_thread = threading.Thread(
            target=self._visualization_loop,
            daemon=True
        )
        self.visualization_thread.start()
        
    def stop(self):
        """停止可视化"""
        self.is_running = False
        if self.ani:
            self.ani.event_source.stop()
        if self.fig:
            plt.close(self.fig)
        if self.visualization_thread and self.visualization_thread.is_alive():
            self.visualization_thread.join(timeout=1.0)  # 等待最多1秒
        
    def get_statistics(self):
        """
        获取统计信息
        
        Returns:
            dict: 包含各种统计数据的字典
        """
        if len(self.intervals) <= 1:  # 至少需要2个数据点
            return {}
            
        # 移除第一个间隔值（通常为0）
        intervals = list(self.intervals)[1:] if len(self.intervals) > 1 else []
        framerates = list(self.framerates)[1:] if len(self.framerates) > 1 else []
        
        if not intervals:
            return {}
            
        return {
            'total_packets': len(self.timestamps),
            'average_interval_ms': float(np.mean(intervals)),
            'std_interval_ms': float(np.std(intervals)),
            'min_interval_ms': float(np.min(intervals)),
            'max_interval_ms': float(np.max(intervals)),
            'average_framerate': float(np.mean(framerates)),
            'std_framerate': float(np.std(framerates)),
            'min_framerate': float(np.min(framerates)),
            'max_framerate': float(np.max(framerates)),
            'duration_seconds': float(self.timestamps[-1] - self.timestamps[0]) if self.timestamps else 0
        }


if __name__ == "__main__":
    # 示例用法
    analyzer = VRPacketAnalyzer()
    
    # 模拟一些VR数据包
    import random
    start_time = time.time()
    
    for i in range(100):
        # 模拟大约90FPS的数据包（~11ms间隔）
        simulated_interval = 0.011 + random.uniform(-0.002, 0.002)  # ±2ms抖动
        packet = {
            'timestamp': start_time + i * simulated_interval,
            'data': f'sample_data_{i}'
        }
        analyzer.add_packet(packet)
        time.sleep(0.01)
    
    # 显示统计信息
    stats = analyzer.get_statistics()
    print("VR Packet Statistics:")
    for key, value in stats.items():
        print(f"{key}: {value:.3f}")