import queue
import threading
import time
import os
import csv
import asyncio
import cv2
import json
from typing import Callable

class DataCollect:
    def __init__(self, save_dir="datasets/temp"):
        self._events = {
            "status_change": self._default_callback
        }

        self.video_queue = queue.Queue()
        self.state_queue = queue.Queue()
        self.gripper_queue = queue.Queue()
        self.running = False
        self.save_dir = save_dir
        self.capture_state = 0  # 0: not capturing, 1: capturing
        self.session_timestamp = None
        self.metadata = {}
        self.pose_files = {}  # 为每个臂创建独立的文件
        self.joint_files = {}
        self.gripper_files = {}
        self.video_dir = None
        os.makedirs(self.save_dir, exist_ok=True)
        self.video_consumer_thread = None
        self.state_consumer_thread = None
        self.gripper_consumer_thread = None

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
        事件处理应是非阻塞的，对于耗时操作应该在独立线程中执行
        :param event_name: 事件名称
        :param args: 位置参数
        :param kwargs: 关键字参数
        """
        if event_name in self._events:
            try:
                # self._events[event_name](*args, **kwargs)
                # 异步执行回调函数以避免阻塞事件循环
                callback = self._events[event_name]
                if asyncio.iscoroutinefunction(callback):
                    # 如果是异步函数，在新事件循环中运行
                    thread = threading.Thread(target=self._run_async_callback, args=(callback, args, kwargs), daemon=True)
                    thread.start()
                else:
                    # 同步函数在新线程中运行以避免阻塞
                    thread = threading.Thread(target=callback, args=args, kwargs=kwargs, daemon=True)
                    thread.start()
            except Exception as e:
                self.emit("error", f"事件{event_name}执行失败: {str(e)}")

    def _run_async_callback(self, callback, args, kwargs):
        """运行异步回调函数"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(callback(*args, **kwargs))
            loop.close()
        except Exception as e:
            self.emit("error", f"异步事件回调执行失败: {str(e)}")

    def _default_callback(self, *args, **kwargs) -> None:
        """默认回调函数，什么也不做"""
        pass
    def _default_error_callback(self, error_msg: str) -> None:
        """默认错误回调函数，打印错误信息"""
        print(f"设备{self.__class__.__name__}发生错误: {error_msg}")

    def put_video_frame(self, frame, ts=None, camera_id=0):
        """向视频队列添加帧（frame为numpy数组），附带时间戳和摄像头ID"""
        if ts is None:
            ts = time.time()
        self.video_queue.put((ts, frame, camera_id))

    def put_robot_state(self, state, arm_id=0, ts=None):
        """向机械臂状态队列添加状态（state为包含pose和joint的元组），附带时间戳和臂ID"""
        if ts is None:
            ts = time.time()
        self.state_queue.put((ts, state, arm_id))

    def put_gripper_state(self, gripper_state, arm_id=0, ts=None):
        """向夹爪状态队列添加状态，附带时间戳和臂ID"""
        if ts is None:
            ts = time.time()
        self.gripper_queue.put((ts, gripper_state, arm_id))

    def set_capture_state(self, state) -> bool:
        """设置采集状态"""
        if self.capture_state == state: return False
        self.toggle_capture_state()
        return True

    def get_capture_state(self):
        """获取采集状态"""
        return self.capture_state

    def toggle_capture_state(self):
        """切换采集状态"""
        if self.capture_state == 0:
            self._start_new_session()
            self.capture_state = 1
        else:
            self.capture_state = 0
        self.emit("status_change", self.capture_state)

    def _start_new_session(self):
        """开始新的采集会话，创建时间戳文件夹"""
        self.session_timestamp = time.strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(self.save_dir, self.session_timestamp)
        self.video_dir = os.path.join(session_dir, "frames")
        
        # 为每个臂创建独立的数据文件
        for arm_id in [0, 1]:  # 支持两个臂
            arm_dir = os.path.join(session_dir, f"arm_{arm_id}")
            os.makedirs(arm_dir, exist_ok=True)
            
            self.pose_files[arm_id] = os.path.join(arm_dir, "poses.csv")
            self.joint_files[arm_id] = os.path.join(arm_dir, "joints.csv")
            self.gripper_files[arm_id] = os.path.join(arm_dir, "grippers.csv")
            
            # Create CSV files with headers
            with open(self.pose_files[arm_id], "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "index", "value"])
                
            with open(self.joint_files[arm_id], "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "index", "value"])
                
            with open(self.gripper_files[arm_id], "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "index", "value"])

        os.makedirs(self.video_dir, exist_ok=True)
        
    def register_device(self, device_name, device_info):
        """注册设备信息到元数据中"""
        self.metadata["devices"][device_name] = device_info

    def finish_session(self):
        """结束当前会话，保存元数据"""
        if self.session_timestamp:
            self.metadata["end_time"] = time.time()
            session_dir = os.path.join(self.save_dir, self.session_timestamp)
            metadata_file = os.path.join(session_dir, "metadata.json")
            
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)

    def start(self):
        """启动消费线程"""
        if not self.running:
            self.running = True
            # 启动三个独立的消费线程
            self.video_consumer_thread = threading.Thread(target=self._consume_video, daemon=True)
            self.state_consumer_thread = threading.Thread(target=self._consume_state, daemon=True)
            self.gripper_consumer_thread = threading.Thread(target=self._consume_gripper, daemon=True)
            self.video_consumer_thread.start()
            self.state_consumer_thread.start()
            self.gripper_consumer_thread.start()

    def stop(self):
        """停止消费线程"""
        self.running = False
        if self.video_consumer_thread:
            self.video_consumer_thread.join()
        if self.state_consumer_thread:
            self.state_consumer_thread.join()
        if self.gripper_consumer_thread:
            self.gripper_consumer_thread.join()
        # 结束会话并保存元数据
        self.finish_session()

    def _consume_video(self):
        """消费视频帧线程：不断取出视频队列头部数据并存储到本地"""
        while self.running:
            try:
                ts, frame, camera_id = self.video_queue.get(timeout=0.1)
                # Check capture state before saving
                if self.capture_state == 1 and self.video_dir:
                    # 为每个摄像头创建独立的子目录
                    camera_dir = os.path.join(self.video_dir, f"camera_{camera_id}")
                    os.makedirs(camera_dir, exist_ok=True)
                    # 保存为PNG格式以保留原始数据
                    filename = os.path.join(camera_dir, f"frame_{ts:.3f}.png")
                    cv2.imwrite(filename, frame)
                self.video_queue.task_done()
            except queue.Empty:
                pass

    def _consume_state(self):
        """消费机械臂状态线程：不断取出状态队列头部数据并存储到本地"""
        while self.running:
            try:
                ts, state, arm_id = self.state_queue.get(timeout=0.1)
                # Check capture state before saving
                if self.capture_state == 1 and arm_id in self.pose_files and arm_id in self.joint_files:
                    # state是一个包含(timestamp, (pose, joints))的元组
                    # pose是位姿数组，joints是关节数组
                    if isinstance(state, tuple) and len(state) >= 2:
                        pose_data, joint_data = state
                        
                        # 写入位姿数据到poses.csv
                        if isinstance(pose_data, (list, tuple)):
                            with open(self.pose_files[arm_id], "a", newline="", encoding="utf-8") as f:
                                writer = csv.writer(f)
                                for i, value in enumerate(pose_data):
                                    writer.writerow([f"{ts:.3f}", i, value])
                                    
                        # 写入关节数据到joints.csv
                        if isinstance(joint_data, (list, tuple)):
                            with open(self.joint_files[arm_id], "a", newline="", encoding="utf-8") as f:
                                writer = csv.writer(f)
                                for i, value in enumerate(joint_data):
                                    writer.writerow([f"{ts:.3f}", i, value])
                        
                self.state_queue.task_done()
            except queue.Empty:
                pass

    def _consume_gripper(self):
        """消费夹爪状态线程：不断取出夹爪队列头部数据并存储到本地"""
        while self.running:
            try:
                ts, gripper_state, arm_id = self.gripper_queue.get(timeout=0.1)
                # Check capture state before saving
                if self.capture_state == 1 and arm_id in self.gripper_files:
                    # 写入夹爪数据到grippers.csv
                    if isinstance(gripper_state, (list, tuple, dict)):
                        with open(self.gripper_files[arm_id], "a", newline="", encoding="utf-8") as f:
                            writer = csv.writer(f)
                            if isinstance(gripper_state, dict):
                                # 如果是字典，遍历键值对
                                for key, value in gripper_state.items():
                                    writer.writerow([f"{ts:.3f}", key, value])
                            else:
                                # 如果是列表或元组，遍历索引和值
                                for i, value in enumerate(gripper_state):
                                    writer.writerow([f"{ts:.3f}", i, value])
                        
                self.gripper_queue.task_done()
            except queue.Empty:
                pass