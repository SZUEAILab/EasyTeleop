from .BaseHand import BaseHand
import time
import threading
import numpy as np
import asyncio
from python.revo2 import revo2_utils

class Revo2Direct(BaseHand):
    """直接控制Revo2灵巧手（基于官方SDK）"""

    name = "Revo2灵巧手直连控制"
    description = "通过Revo2官方SDK直接控制，支持位置时间模式"
    need_config = {
        "port_name": {  
            "type": "string",
            "description": "串口名称（如/dev/ttyUSB0或COM3）",
            "default": None  
        },
        "slave_id": { 
            "type": "integer",
            "description": "设备ID（左手0x7e，右手0x7f）",
            "default": 0x7e
        },
        "control_fps": {
            "type": "integer",
            "description": "控制帧率",
            "default": 80
        },
        "hand_side": {  
            "type": "string",
            "description": "左手(left)或右手(right)",
            "default": "left"
        }
    }

    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.control_fps = config["control_fps"]
        self.dT = 1.0 / self.control_fps  # 控制周期（约0.0125s@80Hz）
        
        # 灵巧手接口（Revo2 SDK相关）
        self.client = None  # Modbus客户端实例
        self.slave_id = config["slave_id"]
        self.is_connected = False
        
        # 控制线程与队列
        self.control_thread_running = False
        self.control_thread = None
        self.hand_queue = []  # 存储待发送的手指位置数据
        self.last_fingers = [0]*6  # 记录上一帧位置
        
        # 滤波历史数据
        self.filter_history = []
        self.filter_window = 5  # 滑动窗口大小
        
        # 异步事件循环（SDK接口为异步）
        self.loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.async_thread.start()

    def _run_async_loop(self):
        """运行异步事件循环的线程"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def set_config(self, config):
        """验证并设置配置"""
        for key in self.need_config:
            if key not in config:
                raise ValueError(f"缺少配置字段: {key}")
        self.slave_id = config["slave_id"]
        self.config = config
        return True

    def _connect_device(self) -> bool:
        """连接灵巧手（基于Revo2 SDK）"""
        try:
            # 使用SDK的连接函数（自动检测或指定串口）
            future = asyncio.run_coroutine_threadsafe(
                revo2_utils.open_modbus_revo2(port_name=self.config["port_name"]),
                self.loop
            )
            client, detected_id = future.result(timeout=5)  # 5秒超时
            self.client = client
            self.slave_id = detected_id or self.slave_id  # 自动检测ID
            
            # 配置控制模式（千分比模式，0-1000范围）
            future = asyncio.run_coroutine_threadsafe(
                self.client.set_finger_unit_mode(self.slave_id, revo2_utils.libstark.FingerUnitMode.Normalized),
                self.loop
            )
            future.result()
            
            self.is_connected = True
            print(f"[Revo2Direct] 灵巧手连接成功: ID={self.slave_id:02x}")
            
            # 启动状态监控
            self.start_monitor()
            return True
        except Exception as e:
            print(f"[Revo2Direct] 连接错误: {str(e)}")
            self.is_connected = False
            return False

    def _disconnect_device(self) -> bool:
        """断开连接"""
        if self.client:
            # 关闭Modbus连接
            revo2_utils.libstark.modbus_close(self.client)
            self.client = None
            self.is_connected = False
            print("[Revo2Direct] 灵巧手已断开")
        # 停止事件循环
        if self.loop.is_running():
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.async_thread.is_alive():
            self.async_thread.join(timeout=1.0)
        return True

    def start_control(self) -> None:
        """启动控制线程（80Hz循环发送指令）"""
        if not self.control_thread_running and self.is_connected:
            self.control_thread_running = True
            self.control_thread = threading.Thread(
                target=self._control_loop,
                daemon=True
            )
            self.control_thread.start()
            print(f"[Revo2Direct] 控制线程启动（{self.control_fps}Hz）")

    def stop_control(self) -> None:
        """停止控制线程"""
        if self.control_thread_running:
            self.control_thread_running = False
            if self.control_thread and self.control_thread.is_alive():
                self.control_thread.join(timeout=1.0)
            print("[Revo2Direct] 控制线程停止")

    def _control_loop(self):
        """控制主循环：按80Hz处理队列数据并发送"""
        while self.control_thread_running:
            t_start = time.time()
            
            # 处理最新的手指数据（只取队列最后一帧）
            if self.hand_queue:
                # 取出并清空队列（只保留最新数据）
                target_fingers = self.hand_queue.pop(-1)
                self.hand_queue.clear()
                
                # 滤波处理（减少抖动）
                filtered_fingers = self._smooth_filter(target_fingers)
                
                # 转换为Revo2的千分比范围（0-100 -> 0-1000）
                scaled_positions = [int(v * 10) for v in filtered_fingers]
                
                # 位置时间控制：发送目标位置+执行时间（毫秒）
                self._send_finger_positions(scaled_positions, duration=int(self.dT * 1000))
                
                # 记录当前位置
                self.last_fingers = filtered_fingers
            
            # 控制帧率（补偿代码运行耗时）
            t_elapsed = time.time() - t_start
            if t_elapsed < self.dT:
                time.sleep(self.dT - t_elapsed)

    def _smooth_filter(self, new_fingers):
        """滑动窗口滤波（平滑高频抖动）"""
        self.filter_history.append(new_fingers)
        if len(self.filter_history) > self.filter_window:
            self.filter_history.pop(0)
        # 计算窗口内平均值，限制在0-100
        return np.mean(self.filter_history, axis=0).clip(0, 100).tolist()

    def _send_finger_positions(self, positions, duration):
        """发送位置+时间指令（使用Revo2 SDK接口）"""
        try:
            # 调用SDK的位置+时间控制接口
            future = asyncio.run_coroutine_threadsafe(
                self.client.set_finger_positions_and_durations(
                    self.slave_id,
                    positions=positions,  # [0-1000]的千分比位置
                    durations=[duration]*6  # 每个手指的执行时间（毫秒）
                ),
                self.loop
            )
            future.result(timeout=0.1)  # 100ms超时
        except Exception as e:
            print(f"[Revo2Direct] 指令发送失败: {str(e)}")

    def start_monitor(self):
        """启动状态监控线程"""
        self.monitor_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()

    def _monitor_loop(self):
        """定期获取灵巧手状态"""
        while self.monitor_running and self.is_connected:
            try:
                # 异步获取电机状态
                future = asyncio.run_coroutine_threadsafe(
                    self.client.get_motor_status(self.slave_id),
                    self.loop
                )
                status = future.result(timeout=0.5)
                
                # 解析状态信息（位置、速度、电流等）
                state_data = {
                    "positions": [p / 10 for p in status.positions],  # 转换为0-100范围
                    "speeds": list(status.speeds),
                    "currents": list(status.currents),
                    "is_idle": status.is_idle()
                }
                self.emit("hand_state", state_data)
            except Exception as e:
                print(f"[Revo2Direct] 状态获取失败: {str(e)}")
            time.sleep(0.1)  # 10Hz状态更新

    def handle_openxr(self, hand_data: dict) -> list:
        """
        基于dex retargeting的映射逻辑：将OpenXR手部数据转换为灵巧手控制值
        返回6个0-100的值，对应[拇指收拢, 食指弯曲, 中指弯曲, 无名指弯曲, 小指弯曲, 无名指联动]
        """
        if not hand_data or not hand_data.get('isTracked') or not hand_data.get('joints'):
            return [0] * 6
    
        joints = hand_data['joints']
        # 校验OpenXR关节数量（标准为26个）
        if len(joints) != 26:
            return [0] * 6
    
        return self._dex_retargeting(joints, hand_data)

    def _dex_retargeting(self, joints, hand_data):
        """dex retargeting核心逻辑：基于OpenXR标准关节计算控制值"""
        # 定义OpenXR关节索引常量（符合XR_EXT_hand_tracking规范）
        XR_HAND_JOINT_PALM = 0
        XR_HAND_JOINT_WRIST = 1
        XR_HAND_JOINT_THUMB_METACARPAL = 2
        XR_HAND_JOINT_THUMB_PROXIMAL = 3
        XR_HAND_JOINT_THUMB_DISTAL = 4
        XR_HAND_JOINT_THUMB_TIP = 5
        XR_HAND_JOINT_INDEX_METACARPAL = 6
        XR_HAND_JOINT_INDEX_PROXIMAL = 7
        XR_HAND_JOINT_INDEX_INTERMEDIATE = 8
        XR_HAND_JOINT_INDEX_DISTAL = 9
        XR_HAND_JOINT_INDEX_TIP = 10
        XR_HAND_JOINT_MIDDLE_METACARPAL = 11
        XR_HAND_JOINT_MIDDLE_PROXIMAL = 12
        XR_HAND_JOINT_MIDDLE_INTERMEDIATE = 13
        XR_HAND_JOINT_MIDDLE_DISTAL = 14
        XR_HAND_JOINT_MIDDLE_TIP = 15
        XR_HAND_JOINT_RING_METACARPAL = 16
        XR_HAND_JOINT_RING_PROXIMAL = 17
        XR_HAND_JOINT_RING_INTERMEDIATE = 18
        XR_HAND_JOINT_RING_DISTAL = 19
        XR_HAND_JOINT_RING_TIP = 20
        XR_HAND_JOINT_LITTLE_METACARPAL = 21
        XR_HAND_JOINT_LITTLE_PROXIMAL = 22
        XR_HAND_JOINT_LITTLE_INTERMEDIATE = 23
        XR_HAND_JOINT_LITTLE_DISTAL = 24
        XR_HAND_JOINT_LITTLE_TIP = 25

        try:
            # 优先使用hand_data中的fingers简化数据（若存在）
            if 'fingers' in hand_data:
                index_bend = hand_data['fingers'][1]['fullCurl'] * 100
                middle_bend = hand_data['fingers'][2]['fullCurl'] * 100
                ring_bend = hand_data['fingers'][3]['fullCurl'] * 100
                little_bend = hand_data['fingers'][4]['fullCurl'] * 100
            else:
                # 计算各手指弯曲程度（多关节角度融合）
                index_bend = self._calculate_finger_bend(
                    joints[XR_HAND_JOINT_INDEX_METACARPAL],
                    joints[XR_HAND_JOINT_INDEX_PROXIMAL],
                    joints[XR_HAND_JOINT_INDEX_INTERMEDIATE],
                    joints[XR_HAND_JOINT_INDEX_DISTAL]
                )
                middle_bend = self._calculate_finger_bend(
                    joints[XR_HAND_JOINT_MIDDLE_METACARPAL],
                    joints[XR_HAND_JOINT_MIDDLE_PROXIMAL],
                    joints[XR_HAND_JOINT_MIDDLE_INTERMEDIATE],
                    joints[XR_HAND_JOINT_MIDDLE_DISTAL]
                )
                ring_bend = self._calculate_finger_bend(
                    joints[XR_HAND_JOINT_RING_METACARPAL],
                    joints[XR_HAND_JOINT_RING_PROXIMAL],
                        joints[XR_HAND_JOINT_RING_INTERMEDIATE],
                    joints[XR_HAND_JOINT_RING_DISTAL]
                )
                little_bend = self._calculate_finger_bend(
                    joints[XR_HAND_JOINT_LITTLE_METACARPAL],
                    joints[XR_HAND_JOINT_LITTLE_PROXIMAL],
                    joints[XR_HAND_JOINT_LITTLE_INTERMEDIATE],
                    joints[XR_HAND_JOINT_LITTLE_DISTAL]
                )

            # 计算拇指收拢程度（基于法向量夹角）
            thumb_adduction = self._calculate_thumb_adduction(
                joints[XR_HAND_JOINT_WRIST],
                joints[XR_HAND_JOINT_PALM],
                joints[XR_HAND_JOINT_THUMB_METACARPAL],
                joints[XR_HAND_JOINT_THUMB_PROXIMAL],
                joints[XR_HAND_JOINT_INDEX_PROXIMAL]  # 引入食指参考点提升精度
            )

            # 应用灵敏度校准（可根据硬件特性调整）
            index_bend = self._calibrate_bend(index_bend, 5, 2.5)
            middle_bend = self._calibrate_bend(middle_bend, 5, 2.5)
            ring_bend = self._calibrate_bend(ring_bend, 5, 2.5)
            little_bend = self._calibrate_bend(little_bend, 5, 2.5)
            thumb_adduction = self._calibrate_bend(thumb_adduction, 5, 1.5)

            # 构造输出（保持原顺序：[拇指收拢, 食指, 中指, 无名指, 小指, 无名指联动]）
            finger_values = [
                thumb_adduction,
                index_bend,
                middle_bend,
                ring_bend,
                little_bend,
                ring_bend  # 无名指与小指联动
            ]

            # 严格限制范围并转为整数
            return [np.clip(int(v), 0, 100) for v in finger_values]

        except Exception as e:
            print(f"[dex retargeting] 计算错误: {str(e)}")
            return [0] * 6

    def _get_joint_position(self, joint):
        """获取关节3D位置向量"""
        return np.array([joint['position']['x'], joint['position']['y'], joint['position']['z']])

    def _angle_between_vectors(self, v1, v2):
        """计算两个向量的夹角（弧度）"""
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)  # 加小值防除零
        cos_angle = np.clip(cos_angle, -1.0, 1.0)  # 避免数值误差
        return np.arccos(cos_angle)

    def _calculate_finger_bend(self, metacarpal, proximal, intermediate, distal):
        """计算手指弯曲程度（融合近节-中节、中节-远节两个关节角度）"""
        # 计算骨向量
        vec1 = self._get_joint_position(proximal) - self._get_joint_position(metacarpal)
        vec2 = self._get_joint_position(intermediate) - self._get_joint_position(proximal)
        vec3 = self._get_joint_position(distal) - self._get_joint_position(intermediate)
    
        # 计算两个关节的夹角
        angle1 = self._angle_between_vectors(vec1, vec2)
        angle2 = self._angle_between_vectors(vec2, vec3)
    
        # 映射为0-100的弯曲值（角度越大弯曲越明显）
        total_angle = angle1 + angle2
        return np.interp(total_angle, [0, np.pi], [0, 100])  # 最大约π弧度（180°）

    def _calculate_thumb_adduction(self, wrist, palm, thumb_m, thumb_p, index_prox):
        """计算拇指向掌心收拢程度（基于手掌与拇指-食指平面的法向量夹角）"""
        # 手掌平面法向量（腕部→手掌、腕部→食指根部）
        palm_vec1 = self._get_joint_position(palm) - self._get_joint_position(wrist)
        palm_vec2 = self._get_joint_position(index_prox) - self._get_joint_position(wrist)
        palm_normal = np.cross(palm_vec1, palm_vec2)
    
        # 拇指-食指平面法向量（拇指掌骨→拇指近节、拇指掌骨→食指根部）
        thumb_vec = self._get_joint_position(thumb_p) - self._get_joint_position(thumb_m)
        index_vec = self._get_joint_position(index_prox) - self._get_joint_position(thumb_m)
        thumb_index_normal = np.cross(index_vec, thumb_vec)
    
        # 防止零向量（避免计算错误）
        if np.linalg.norm(palm_normal) < 1e-6 or np.linalg.norm(thumb_index_normal) < 1e-6:
            return 50.0  # 默认中间值
    
        # 计算法向量夹角（反映拇指收拢程度）
        angle = self._angle_between_vectors(palm_normal, thumb_index_normal)
        # 映射为0-100（角度越小，收拢越充分）
        return np.interp(angle, [0, np.pi/2], [100, 0])

    def _calibrate_bend(self, value, offset, scale):
        """校准弯曲值灵敏度（偏移量+缩放）"""
        calibrated = (value - offset) * scale
        return np.clip(calibrated, 0, 100)

    def add_hand_data(self, data):
        """添加手指控制数据到队列"""
        self.hand_queue.append(data)

    def _main(self):
        """设备主循环"""
        while self.running:
            time.sleep(0.1)