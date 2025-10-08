import asyncio
import threading
import time
import math
from typing import Dict, Any, Tuple, Callable
from scipy.spatial.transform import Rotation as R  # 需要安装 scipy

class TeleopMiddleware:
    def __init__(self,left_wrist_controller = None,right_wrist_controller = None):
        # 用字典存储事件与回调的映射，格式: {事件名: [回调1, 回调2, ...]}
        self._events = {
             "buttonAUp": self._default_callback,
            "buttonADown": self._default_callback,
            "buttonATurnDown": self._default_callback,
            "buttonATurnUp": self._default_callback,
            "buttonBUp": self._default_callback,
            "buttonBDown": self._default_callback,
            "buttonBTurnDown": self._default_callback,
            "buttonBTurnUp": self._default_callback,
            "buttonXUp": self._default_callback,
            "buttonXDown": self._default_callback,
            "buttonXTurnDown": self._default_callback,
            "buttonXTurnUp": self._default_callback,
            "buttonYUp": self._default_callback,
            "buttonYDown": self._default_callback,
            "buttonYTurnDown": self._default_callback,
            "bttonYTurnUp": self._default_callback,  # 注意原字段拼写
            "leftGripUp": self._default_callback,
            "leftGripDown": self._default_callback,
            "leftGripTurnDown": self._default_callback,
            "leftGripTurnUp": self._default_callback,
            "rightGripUp": self._default_callback,
            "rightGripDown": self._default_callback,
            "rightGripTurnDown": self._default_callback,
            "rightGripTurnUp":self._default_callback,
            "leftStick":self._default_callback,
            "rightStick":self._default_callback,
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
        事件处理应是非阻塞的，对于耗时操作应该在独立线程中执行
        :param event_name: 事件名称
        :param args: 位置参数
        :param kwargs: 关键字参数
        """
        if event_name in self._events:
            try:
                self._events[event_name](*args, **kwargs)
                # # 异步执行回调函数以避免阻塞事件循环
                # callback = self._events[event_name]
                # if asyncio.iscoroutinefunction(callback):
                #     # 如果是异步函数，在新事件循环中运行
                #     thread = threading.Thread(target=self._run_async_callback, args=(callback, args, kwargs), daemon=True)
                #     thread.start()
                # else:
                #     # 同步函数在新线程中运行以避免阻塞
                #     thread = threading.Thread(target=callback, args=args, kwargs=kwargs, daemon=True)
                #     thread.start()
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
        
    def _default_callback(self,*args, **kwargs):
        pass

    def start(self):
        # 多线程
        # self.sender_thread = threading.Thread(target=self.feedback_thread_func, args=(self.sock,), daemon=True)
        
        # self.sender_thread.start()
        
                
                
        
        while True:
            time.sleep(1)
            # self.sender_thread.join(1)
            # self.receiver_thread.join(1)

    # def feedback_thread_func(self, sock ,delay = 0.05):
    #     while True:
    #         try:
    #             # 读取当前位置并反馈
    #             left_state = self.left_wrist_controller.get_state()
    #             right_state = self.right_wrist_controller.get_state()
    #             left_quat = euler_to_quat(left_state[3], left_state[4], left_state[5])
    #             right_quat = euler_to_quat(right_state[3], right_state[4], right_state[5])
                
    #             feedback = {
    #                 "leftPos":{
    #                     "x": left_state[0],
    #                     "y": left_state[1],
    #                     "z": left_state[2],
    #                 },
    #                 "leftRot":{
    #                     "x": left_state[3]*180/math.pi,
    #                     "y": left_state[4]*180/math.pi,
    #                     "z": left_state[5]*180/math.pi,
    #                 },
    #                 "leftQuat": left_quat,
    #                 "rightPos":{
    #                     "x": right_state[0],
    #                     "y": right_state[1],
    #                     "z": right_state[2],
    #                 },
    #                 "rightRot":{
    #                     "x": right_state[3]*180/math.pi,
    #                     "y": right_state[4]*180/math.pi,
    #                     "z": right_state[5]*180/math.pi,
    #                 },
    #                 "rightQuat": right_quat
    #             }
    #             feedback_json = json.dumps(feedback) + "\n"
    #             sock.sendall(feedback_json.encode("utf-8"))
    #             time.sleep(delay)
    #         except KeyboardInterrupt:
    #             break
    
    def handle_socket_data(self, data_dict):
        """
        处理从 socket 接收到的数据，并根据事件字段触发回调
        """
        try:
            # 提取左臂位置和旋转角度
            left_pos = data_dict['leftPos']
            left_rot = data_dict['leftRot']
            left_quat = data_dict['leftQuat']
            x_l, y_l, z_l = left_pos['x'], left_pos['y'], left_pos['z']
            # roll_l, pitch_l, yaw_l = left_rot['x']*math.pi/180, left_rot['y']*math.pi/180, left_rot['z']*math.pi/180
            quat_l = [left_quat['x'], left_quat['y'], left_quat['z'], left_quat['w']]
            roll_l,pitch_l, yaw_l = euler_from_quaternion(quat_l)
            # roll_l = -roll_l  # 翻转 pitch 角度

            # 提取右臂位置和旋转角度
            right_pos = data_dict['rightPos']
            right_rot = data_dict['rightRot']
            right_quat = data_dict['rightQuat']
            x_r, y_r, z_r = right_pos['x'], right_pos['y'], right_pos['z']
            # roll_r, pitch_r, yaw_r = right_rot['x']*math.pi/180, right_rot['y']*math.pi/180, right_rot['z']*math.pi/180
            quat_r = [right_quat['x'], right_quat['y'], right_quat['z'], right_quat['w']]
            roll_r,pitch_r, yaw_r = euler_from_quaternion(quat_r)
            # roll_r = -roll_r  # 翻转 pitch 角度

            # 提取抓手状态
            left_trigger = 1 - data_dict['leftTrigger']
            right_trigger = 1 - data_dict['rightTrigger']

            if (x_l == 0 and y_l == 0 and z_l == 0) : # the position missing, discared
                debug_print("左手坐标为0，丢弃该条信息", True)
            else:
                if data_dict['leftGrip']==True:
                    self.emit("leftGripDown",[x_l, y_l, z_l, roll_l, pitch_l, yaw_l],left_trigger)
                    # self.left_wrist_controller.start_control([x_l, y_l, z_l, roll_l, pitch_l, yaw_l],left_trigger)
                else:
                    self.emit("leftGripUp")
                    # self.left_wrist_controller.stop_control()
                        

            
            if x_r == 0 and y_r == 0 and z_r == 0:
                debug_print("右手坐标为0，丢弃该条信息", True)
            else:
                if data_dict['rightGrip']==True:
                    self.emit("rightGripDown",[x_r, y_r, z_r, roll_r, pitch_r, yaw_r],right_trigger)
                    # self.right_wrist_controller.start_control([x_r, y_r, z_r, roll_r, pitch_r, yaw_r],right_trigger)
                else:
                    self.emit("rightGripUp")
                    # self.right_wrist_controller.stop_control()


        except Exception as e:
            debug_print(f"处理数据时出错: {e}", True)

        try:
            # 状态类事件（Up/Down）
            state_events = [
                ("buttonA", "buttonADown", "buttonAUp"),
                ("buttonB", "buttonBDown", "buttonBUp"),
                ("buttonX", "buttonXDown", "buttonXUp"),
                ("buttonY", "buttonYDown", "buttonYUp"),
            ]
            for field, down_evt, up_evt in state_events:
                if field in data_dict:
                    if data_dict[field]:
                        self.emit(down_evt)
                    else:
                        self.emit(up_evt)

            # 触发类事件（TurnDown/TurnUp等，只在True时触发）
            trigger_events = [
                "buttonATurnDown", "buttonATurnUp",
                "buttonBTurnDown", "buttonBTurnUp",
                "buttonXTurnDown", "buttonXTurnUp",
                "buttonYTurnDown", "buttonYTurnUp",
                "rightGripTurnDown", "rightGripTurnUp",
                "leftGripTurnDown", "leftGripTurnUp"
            ]
            for evt in trigger_events:
                if data_dict.get(evt, False):
                    self.emit(evt)

            if "leftStick" in data_dict:
                self.emit("leftStick",data_dict["leftStick"])
            if "rightStick" in data_dict:
                self.emit("rightStick",data_dict["rightStick"])

        except Exception as e:
            debug_print(f"处理数据时出错: {e}", True)
    



    

DEBUG = False

def euler_from_quaternion(quat):
    """
    手动实现四元数转欧拉角（XYZ旋转顺序，右手坐标系）
    :param quat: 四元数列表，格式为 [x, y, z, w]（实部为w，虚部为x/y/z）
    :return: 欧拉角 (roll, pitch, yaw)，单位为弧度（对应X/Y/Z轴旋转）
    """
    x, y, z, w = quat  # 解包四元数分量
    
    # 1. 计算滚转角（roll，X轴旋转）
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)  # 范围：[-π, π]
    
    # 2. 计算俯仰角（pitch，Y轴旋转）
    sinp = 2 * (w * y - z * x)
    # 防止数值溢出（因浮点计算误差，sinp可能超出[-1,1]）
    sinp = min(max(sinp, -1.0), 1.0)
    pitch = math.asin(sinp)  # 范围：[-π/2, π/2]
    
    # 3. 计算偏航角（yaw，Z轴旋转）
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)  # 范围：[-π, π]
    
    return roll, pitch, yaw

def euler_to_quat(rx, ry, rz):
    # 欧拉角转四元数，单位为度
    r = R.from_euler('xyz', [rx, ry, rz], degrees=True)
    q = r.as_quat()  # [x, y, z, w]
    return {"x": q[0], "y": q[1], "z": q[2], "w": q[3]}

def debug_print(msg, release=False):
    if release or DEBUG:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [DEBUG] {msg}")

