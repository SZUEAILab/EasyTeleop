from .BaseHand import BaseHand
import time
import numpy as np
import asyncio
import threading
from .bc.revo2 import revo2_utils

class Revo2Direct(BaseHand):
    """异步直接控制Revo2灵巧手（基于官方SDK）"""

    name = "Revo2灵巧手直连控制"
    description = "通过Revo2官方SDK异步控制，支持位置时间模式"
    need_config = {
        "port": {  
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
        self.control_fps = config["control_fps"]
        self.dT = 1.0 / self.control_fps  # 控制周期
        
        # 灵巧手接口
        self.client = None
        self.slave_id = config["slave_id"]
        
        # 控制任务与队列
        self.control_task = None
        self.control_running = False
        self._control_future = None
        self._control_requested = False
        self.hand_queue = []
        self.last_fingers = [0]*6
        
        # 滤波相关
        self.filter_history = []
        self.filter_window = 5
        
        # 监控任务
        self.monitor_task = None
        self.monitor_running = False

        # 异步事件循环
        self.control_loop = None
        # SDK 专用事件循环（长期运行，用于 libstark 客户端）
        self._sdk_loop = None
        self._sdk_thread = None

    def set_config(self, config):
        """验证并设置配置（同步接口，满足 BaseDevice 约束）"""
        for key in self.need_config:
            if key not in config:
                raise ValueError(f"缺少配置字段: {key}")
        self.slave_id = config["slave_id"]
        self.config = config
        return True

    def _run_coro_sync(self, coro):
        """在 SDK 的后台事件循环中运行协程并返回结果（线程安全）。

        使用单一长期运行的事件循环来创建并管理 client 对象，避免 client 绑定到已关闭的 loop
        导致 "no running event loop" 错误。
        """
        # 创建 SDK 事件循环（如果尚未创建）
        if self._sdk_loop is None:
            self._ensure_sdk_loop()

        # 使用 run_coroutine_threadsafe 在后台 loop 中调度协程并等待结果
        future = asyncio.run_coroutine_threadsafe(coro, self._sdk_loop)
        try:
            return future.result(timeout=5)
        except Exception:
            # 在超时或异常时取消任务并抛出异常
            try:
                future.cancel()
            except Exception:
                pass
            raise

    def _call_client_async(self, coro_func, *args, **kwargs):
        """确保 client 的异步方法在 SDK loop 中执行，避免在主线程求值"""

        async def _runner():
            return await coro_func(*args, **kwargs)

        return self._run_coro_sync(_runner())

    def _ensure_sdk_loop(self):
        """创建并启动用于 SDK 的后台事件循环（长期运行线程）。"""
        if self._sdk_loop is not None:
            return

        loop = asyncio.new_event_loop()
        self._sdk_loop = loop

        def _run_loop():
            asyncio.set_event_loop(loop)
            try:
                loop.run_forever()
            finally:
                # 在 loop 停止后，关闭 loop
                try:
                    loop.close()
                except Exception:
                    pass

        t = threading.Thread(target=_run_loop, daemon=True)
        self._sdk_thread = t
        t.start()

    def _connect_device(self) -> bool:
        """同步连接灵巧手（在内部运行 SDK 的异步接口）"""
        try:
            # 使用新的事件循环运行 SDK 的异步打开函数
            client, detected_id = self._run_coro_sync(
                revo2_utils.open_modbus_revo2(port_name=self.config["port"])
            )
            self.client = client
            self.slave_id = detected_id or self.slave_id

            # 配置控制模式（通过同步运行协程）
            self._call_client_async(
                self.client.set_finger_unit_mode,
                self.slave_id,
                revo2_utils.libstark.FingerUnitMode.Normalized,
            )

            print(f"[Revo2Direct] 灵巧手连接成功: ID={self.slave_id:02x}")
            # 如果用户已经请求开启控制，则在连接完成后自动启动控制
            if self._control_requested and not self.control_running:
                self._start_control_task()
            return True
        except Exception as e:
            print(f"[Revo2Direct] 连接错误: {str(e)}")
            return False
            return False

    def _disconnect_device(self) -> bool:
        """同步断开连接并停止控制/监控"""
        if self.client:
            try:
                revo2_utils.libstark.modbus_close(self.client)
            except Exception:
                pass
            self.client = None
            print("[Revo2Direct] 灵巧手已断开")

        # 关闭 SDK 后台事件循环
        try:
            if self._sdk_loop is not None:
                try:
                    self._sdk_loop.call_soon_threadsafe(self._sdk_loop.stop)
                except Exception:
                    pass
                if self._sdk_thread is not None and self._sdk_thread.is_alive():
                    self._sdk_thread.join(timeout=1.0)
                self._sdk_thread = None
                self._sdk_loop = None
        except Exception:
            pass

        # 停止所有任务（同步接口）
        try:
            self._stop_control_task()
        except Exception:
            pass
        return True

    def start_control(self) -> None:
        """启动控制任务；若尚未连接则在连接完成后自动启动。"""
        self._control_requested = True
        if self.get_conn_status() != 1:
            print("[Revo2Direct] 连接未完成，控制任务将在连接成功后自动启动")
            return
        self._start_control_task()

    def _start_control_task(self):
        """实际启动控制循环任务（运行在 SDK loop 中）"""
        if self.control_running:
            return
        self.control_running = True
        self._ensure_sdk_loop()
        try:
            self._control_future = asyncio.run_coroutine_threadsafe(self._control_loop(), self._sdk_loop)
        except Exception as e:
            print(f"[Revo2Direct] 启动控制任务失败: {e}")
            self.control_running = False
            self._control_future = None
            return
        print(f"[Revo2Direct] 控制任务启动（{self.control_fps}Hz）")

    def _control_thread_entry(self):
        # 旧的线程入口已废弃，控制任务现在运行在 SDK 的长期事件循环中
        pass

    def stop_control(self) -> None:
        """停止控制任务（同步接口）"""
        self._control_requested = False
        self._stop_control_task()

    def _stop_control_task(self):
        """内部方法：停止控制协程，但保留控制请求状态"""
        if not self.control_running:
            self._control_future = None
            return
        self.control_running = False
        if self._control_future is not None:
            try:
                self._control_future.cancel()
            except Exception:
                pass
            try:
                self._control_future.result(timeout=1.0)
            except Exception:
                pass
            self._control_future = None
        print("[Revo2Direct] 控制任务停止")

    async def _control_loop(self):
        """异步控制主循环（运行在独立事件循环里）"""
        while self.control_running:
            t_start = time.time()

            # 处理最新的手指数据
            if self.hand_queue:
                # 取出最新数据（BaseHand 使用 deque, 这里保持兼容）
                try:
                    target_fingers = self.hand_queue.pop()
                except Exception:
                    target_fingers = None
                # 清空队列
                try:
                    self.hand_queue.clear()
                except Exception:
                    pass

                if target_fingers is not None:
                    # 滤波处理
                    filtered_fingers = self._smooth_filter(target_fingers)

                    # 转换为千分比范围
                    scaled_positions = [int(v * 10) for v in filtered_fingers]

                    # 发送位置指令（调用 SDK 的异步接口）
                    try:
                        await asyncio.wait_for(
                            self.client.set_finger_positions_and_durations(
                                self.slave_id,
                                positions=scaled_positions,
                                durations=[int(self.dT * 1000)] * 6
                            ),
                            timeout=0.1,
                        )
                    except Exception as e:
                        print(f"[Revo2Direct] 指令发送失败: {str(e)}")

                    self.last_fingers = filtered_fingers

            # 控制帧率
            t_elapsed = time.time() - t_start
            sleep_time = self.dT - t_elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    def _smooth_filter(self, new_fingers):
        """滑动窗口滤波"""
        self.filter_history.append(new_fingers)
        if len(self.filter_history) > self.filter_window:
            self.filter_history.pop(0)
        return np.mean(self.filter_history, axis=0).clip(0, 100).tolist()


    def handle_openxr(self, hand_data: dict) -> list:
        """
        根据OpenXR手部骨架数据计算灵巧手控制值
        返回6个0-100的值，前五个表示手指弯曲程度，第六个表示大拇指向掌心收拢的程度
        
        Args:
            hand_data: OpenXR手部数据，包含joints数组和rootPose
            
        Returns:
            list: 6个0-100的值，分别对应拇指收拢、拇指弯曲、中指弯曲、食指弯曲、小指弯曲、无名指弯曲
        """
        if not hand_data or not hand_data.get('isTracked') or not hand_data.get('joints'):
            return [0, 0, 0, 0, 0, 0]
        
        joints = hand_data['joints']
        if len(joints) != 26:  # OpenXR定义的26个关节
            return [0, 0, 0, 0, 0, 0]
        
        # OpenXR关节索引常量
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
        
        def get_joint_position(joint):
            """获取关节位置"""
            return np.array([joint['position']['x'], joint['position']['y'], joint['position']['z']])
        def calculate_bone_bend(joint1, joint2, joint3):
            vec1 = get_joint_position(joint2) - get_joint_position(joint1)
            vec2 = get_joint_position(joint3) - get_joint_position(joint2)
            cos_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            # 限制在[-1, 1]范围内，防止数值误差
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle = np.arccos(cos_angle)
            return angle/ (2 * np.pi) *360
        def calculate_finger_bend(joint1, joint2, joint3, joint4):
            """
            计算手指弯曲程度
            通过计算三个关节角度来确定弯曲程度
            """
            # 计算关节向量
            vec1 = get_joint_position(joint2) - get_joint_position(joint1)
            vec2 = get_joint_position(joint3) - get_joint_position(joint2)
            vec3 = get_joint_position(joint4) - get_joint_position(joint3)
            
            # 计算关节间角度
            # 使用向量夹角公式: cos(theta) = (a·b)/(|a||b|)
            def angle_between_vectors(v1, v2):
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                # 限制在[-1, 1]范围内，防止数值误差
                cos_angle = np.clip(cos_angle, -1.0, 1.0)
                angle = np.arccos(cos_angle)
                return angle
            
            angle1 = angle_between_vectors(vec1, vec2)
            angle2 = angle_between_vectors(vec2, vec3)
            
            # 将角度转换为0-100的弯曲程度值
            # 弯曲角度越大，值越接近100
            bend_value = (angle1 + angle2) / (2 * np.pi) * 100
            return np.clip(bend_value, 0, 100)
        
        def calculate_thumb_towards_palm(wrist, palm, thumb_m, thumb_p, thumb_d):
            """
            计算拇指收拢程度（向掌心方向）
            通过计算thumb_index_normal和palm_normal两个法向量的夹角来确定
            """
            try:
                # 获取关节位置
                wrist_pos = get_joint_position(wrist)
                palm_pos = get_joint_position(palm)
                thumb_m_pos = get_joint_position(thumb_m)
                thumb_p_pos = get_joint_position(thumb_p)
                
                # 计算手掌平面的法向量（使用手腕、手掌和食指根部）
                index_proximal_pos = get_joint_position(joints[XR_HAND_JOINT_INDEX_PROXIMAL_EXT])
                palm_vec1 = palm_pos - wrist_pos
                palm_vec2 = index_proximal_pos - wrist_pos
                palm_normal = np.cross(palm_vec1, palm_vec2)
                
                # 检查零向量
                if np.linalg.norm(palm_normal) == 0:
                    return 50.0  # 返回默认值
                
                # 计算拇指第一根骨头和食指第一根骨头的平面法向量（从metacarpal到proximal）
                thumb_bone_vec = thumb_p_pos - thumb_m_pos
                index_bone_vec = index_proximal_pos - thumb_m_pos

                thumb_index_normal = np.cross(index_bone_vec,thumb_bone_vec)
                
                # 计算thumb_index_normal和palm_normal两个法向量的夹角
                cos_angle = np.dot(palm_normal, thumb_index_normal) / (
                    np.linalg.norm(palm_normal) * np.linalg.norm(thumb_index_normal)
                )
                cos_angle = np.clip(cos_angle, -1.0, 1.0)
                angle = np.arccos(np.abs(cos_angle))  # 使用绝对值计算夹角
                # print(f"angel: {angle}")
                
                # 将夹角映射到0-100范围
                # 0度时为100（完全收拢），90度时为0（完全张开）
                thumb_towards_palm = angle / (np.pi/2) * 100
                return np.clip(thumb_towards_palm, 0, 100)
            except Exception as e:
                # 出现异常时返回默认值
                return 50.0
        
        # 计算各手指弯曲程度
        try:
            
            
            # 拇指弯曲程度 (thumb)
            # thumb_bend = calculate_finger_bend(
            #     joints[XR_HAND_JOINT_THUMB_METACARPAL_EXT],
            #     joints[XR_HAND_JOINT_THUMB_PROXIMAL_EXT],
            #     joints[XR_HAND_JOINT_THUMB_DISTAL_EXT],
            #     joints[XR_HAND_JOINT_THUMB_TIP_EXT]
            # )

            if 'fingers' in hand_data:
                index_bend = hand_data['fingers'][1]['fullCurl']*100
                middle_bend = hand_data['fingers'][2]['fullCurl']*100
                ring_bend = hand_data['fingers'][3]['fullCurl']*100
                little_bend = hand_data['fingers'][4]['fullCurl']*100
                thumb_bend = hand_data['fingers'][0]['fullCurl']*100
            else:
                # 食指弯曲程度 (index finger)
                index_bend = calculate_finger_bend(
                    joints[XR_HAND_JOINT_INDEX_METACARPAL_EXT],
                    joints[XR_HAND_JOINT_INDEX_PROXIMAL_EXT],
                    joints[XR_HAND_JOINT_INDEX_INTERMEDIATE_EXT],
                    joints[XR_HAND_JOINT_INDEX_DISTAL_EXT]
                )

                
                # 中指弯曲程度 (middle finger)
                middle_bend = calculate_finger_bend(
                    joints[XR_HAND_JOINT_MIDDLE_METACARPAL_EXT],
                    joints[XR_HAND_JOINT_MIDDLE_PROXIMAL_EXT],
                    joints[XR_HAND_JOINT_MIDDLE_INTERMEDIATE_EXT],
                    joints[XR_HAND_JOINT_MIDDLE_DISTAL_EXT]
                )
                
                # 无名指弯曲程度 (ring finger)
                ring_bend = calculate_finger_bend(
                    joints[XR_HAND_JOINT_RING_METACARPAL_EXT],
                    joints[XR_HAND_JOINT_RING_PROXIMAL_EXT],
                    joints[XR_HAND_JOINT_RING_INTERMEDIATE_EXT],
                    joints[XR_HAND_JOINT_RING_DISTAL_EXT]
                )
                
                # 小指弯曲程度 (little finger)
                little_bend = calculate_finger_bend(
                    joints[XR_HAND_JOINT_LITTLE_METACARPAL_EXT],
                    joints[XR_HAND_JOINT_LITTLE_PROXIMAL_EXT],
                    joints[XR_HAND_JOINT_LITTLE_INTERMEDIATE_EXT],
                    joints[XR_HAND_JOINT_LITTLE_DISTAL_EXT]
                )
                thumb_bend = calculate_bone_bend(
                    joints[XR_HAND_JOINT_THUMB_METACARPAL_EXT],
                    joints[XR_HAND_JOINT_THUMB_PROXIMAL_EXT],
                    joints[XR_HAND_JOINT_THUMB_DISTAL_EXT]
                )

                index_bend = (index_bend-5)*2.5
                middle_bend = (middle_bend-5)*2.5
                ring_bend = (ring_bend-5)*2.5
                little_bend = (little_bend-5)*2.5
                thumb_bend = (thumb_bend-10)*2
            
            # 拇指收拢程度
            thumb_towards_palm = calculate_thumb_towards_palm(
                joints[XR_HAND_JOINT_WRIST_EXT],
                joints[XR_HAND_JOINT_PALM_EXT],
                joints[XR_HAND_JOINT_THUMB_METACARPAL_EXT],
                joints[XR_HAND_JOINT_THUMB_PROXIMAL_EXT],
                joints[XR_HAND_JOINT_THUMB_DISTAL_EXT]
            )
            thumb_towards_palm = (thumb_towards_palm-5)*1.5
            
            # 返回6个值：拇指收拢、拇指弯曲、中指弯曲、食指弯曲、小指弯曲、无名指弯曲
            thumb_towards_palm = max(0, min(100, int(thumb_towards_palm)))
            thumb_bend = max(0, min(100, int(thumb_bend)))
            middle_bend = max(0, min(100, int(middle_bend)))
            index_bend = max(0, min(100, int(index_bend)))
            little_bend = max(0, min(100, int(little_bend)))
            ring_bend = max(0, min(100, int(ring_bend)))
            return [thumb_bend,thumb_towards_palm, index_bend,middle_bend,  ring_bend,little_bend]
            
        except Exception as e:
            # 如果计算过程中出现错误，返回默认值
            print(f"计算手部控制值时出错: {e}")
            return [50, 0, 0, 0, 0, 0]  # 拇指收拢程度默认为50

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
        return np.interp(angle, [0, np.pi/2], [0, 100]) 

    def _calibrate_bend(self, value, offset, scale):
        """校准弯曲值灵敏度（偏移量+缩放）"""
        calibrated = (value - offset) * scale
        return np.clip(calibrated, 0, 100)

    def add_hand_data(self, data):
        """添加手指控制数据到队列（兼容 BaseHand 的 deque 接口）"""
        try:
            self.hand_queue.append(data)
        except Exception:
            # 如果 hand_queue 不是 deque，则退回到列表追加
            if isinstance(self.hand_queue, list):
                self.hand_queue.append(data)
          
    def set_finger_positions(self, positions: list):
        """直接设置手指位置（同步封装，用于测试）"""
        if self.get_conn_status() != 1:
            print("[Revo2Direct] 未连接，无法发送控制指令")
            return False
        try:
            # 使用 SDK loop 同步运行异步 SDK 接口
            self._call_client_async(self.client.set_finger_positions, self.slave_id, positions)
            print(f"[Revo2Direct] 发送位置指令: {positions}")
            return True
        except Exception as e:
            print(f"[Revo2Direct] 发送指令失败: {e}")
            return False

    def _main(self):
        """设备主逻辑（同步）

        由 BaseDevice._main_loop 在连接成功后调用。这里保持一个简单循环以保持线程活跃，
        控制/监控在各自线程中运行。
        """
        # 将监控轮询合并到主循环中：以同步方式通过 _run_coro_sync 调用 SDK 的异步状态查询
        monitor_interval = 0.1
        last_monitor = 0.0
        try:
            while self.get_conn_status() == 1:
                t_now = time.time()
                # 轮询监控
                # if self.client and (t_now - last_monitor) >= monitor_interval:
                #     last_monitor = t_now
                #     try:
                #         status = self._run_coro_sync(self.client.get_motor_status(self.slave_id))
                #         if status is not None:
                #             state_data = {
                #                 "positions": [p / 10 for p in status.positions],
                #                 "speeds": list(status.speeds),
                #                 "currents": list(status.currents),
                #                 "is_idle": status.is_idle()
                #             }
                #             # emit 是非阻塞的（会在独立线程中运行回调）
                #             self.emit("hand_state", state_data)
                #     except Exception as e:
                #         print(f"[Revo2Direct] 状态获取失败: {str(e)}")

                # 让出时间片，避免忙等待
                time.sleep(0.01)
        except Exception:
            pass
