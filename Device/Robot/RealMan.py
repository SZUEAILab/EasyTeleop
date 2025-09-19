from Robotic_Arm.rm_robot_interface import *
import time
import numpy as np
import threading
from threading import Lock
from typing import Dict, Any
from .BaseRobot import BaseRobot

class RM_controller(BaseRobot):
    """
    RealMan机器人控制器，继承自Robot基类，实现具体控制逻辑。
    """
    # 定义需要的配置字段为静态字段
    need_config = {
        "ip": "服务器IP地址",
        "port": "服务器端口号",
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.ip = None
        self.port = None
        
        self._events = {
            "state": self._default_callback,
        }
        
        self.target_fps = 30  # 目标帧率
        self.min_interval = 1.0 / self.target_fps  # 最小间隔时间
        
        self.arm_controller = None
        self.handle = None
        self.thread_mode = rm_thread_mode_e.RM_TRIPLE_MODE_E
        
        
        # 状态存储变量
        self.current_state = None
        self.current_gripper_state = None
        
        # 线程相关变量
        
        self.polling_thread = None
        self.state_lock = Lock()  # 用于线程安全访问状态变量
        
        # 控制相关变量
        self.is_controlling = False
        self.prev_tech_state = None
        self.arm_first_state = None
        self.gripper_close = False
        self.delta = [0, 0, 0 , 0 , 0 , 0]
        
        # 如果提供了配置，则设置配置
        if config:
            self.set_config(config)
        
        
    def set_config(self, config):
        """
        设置设备配置，验证配置是否符合need_config要求
        :param config: 配置字典
        :return: 是否设置成功
        """
        # 检查必需的配置字段
        for key in self.need_config:
            if key not in config:
                raise ValueError(f"缺少必需的配置字段: {key}")
        
        self.config = config
        self.ip = config["ip"]
        self.port = int(config["port"])
        
        return True
        
    def start(self):
        
        try:
            self.set_conn_status(2)
            if self.polling_thread is None or not self.polling_thread.is_alive():
                self.polling_thread = threading.Thread(target=self._poll_state, daemon=True)
                self.polling_thread.start()
                return True
            return False
        except Exception as e:
            print(f"start failed: {str(e)}")
        
        

    def stop(self):
        """停止设备"""
        self.set_conn_status(0)
        if self.polling_thread is not None:
            self.polling_thread.join()
            self.polling_thread = None
        self.arm_controller.rm_destroy_robot_arm(self.handle)
        
        print("[Shutdown]Robot arm stopped and disconnected.")
        
        return True

    def _poll_state(self):
        last_time = time.time()
        while self.get_conn_status():
            # print(f"[Polling]Robot arm is {'connected' if self.get_conn_status() == 1 else 'disconnected'}, polling state...")
            if self.get_conn_status() ==  1:
                try:
                    succ, arm_state = self.arm_controller.rm_get_current_arm_state()
                    if not succ:
                        
                        with self.state_lock:
                            self.current_state = arm_state["pose"]
                            self.emit("state",self.current_state)#调用回调函数
                    else:
                        raise RuntimeError("Failed to get arm state")
                
                    # 获取夹爪状态
                    succ_gripper, gripper_state = self.arm_controller.rm_get_gripper_state()
                    if not succ_gripper:
                        with self.state_lock:
                            self.current_gripper_state = gripper_state
                    else:
                        raise RuntimeError("Failed to get gripper state")
                    # 帧率控制，而不是固定间隔
                    current_time = time.time()
                    elapsed = current_time - last_time
                    if elapsed < self.min_interval:
                        time.sleep(self.min_interval - elapsed)
                    last_time = time.time()
                except Exception as e:
                    self.set_conn_status(2)
                    print(f"Error polling robot state: {str(e)}")
            else:
                try:
                    self.arm_controller = RoboticArm(self.thread_mode)
                    self.handle = self.arm_controller.rm_create_robot_arm(self.ip, self.port) 
                    if self.handle.id == -1:
                        raise ConnectionError(f"Failed to connect to robot arm at {self.ip}:{self.port}")
                    print(f"[Initialize]Robot arm connected at {self.ip}:{self.port}")

                    # 获取手臂状态
                    succ, arm_state = self.arm_controller.rm_get_current_arm_state()
                    if not succ:
                        with self.state_lock:
                            self.current_state = arm_state["pose"]
                    else:
                        raise RuntimeError("Failed to get arm state")
                    
                    # 获取夹爪状态
                    succ_gripper, gripper_state = self.arm_controller.rm_get_gripper_state()
                    if not succ_gripper:
                        with self.state_lock:
                            self.current_gripper_state = gripper_state
                    else:
                        raise RuntimeError("Failed to get gripper state")
                            
                    self.set_conn_status(1)
                    print("[Initialize]Robot arm initialized and polling started.")
                    
                except Exception as e:
                    time.sleep(self.reconnect_interval)
                
                
    def get_state(self):
        """获取当前状态（线程安全）"""
        with self.state_lock:
            return self.current_state.copy() if self.current_state is not None else None

    def get_gripper(self):
        """获取当前夹爪状态（线程安全）"""
        with self.state_lock:
            return self.current_gripper_state
    
    def start_control(self, state, trigger=None):
        """开始控制手臂，自动判断欧拉角或四元数"""

        if self.is_controlling is False:
            self.is_controlling = True
            self.prev_tech_state = state
            self.arm_first_state = self.get_state()
            self.delta = [0, 0, 0, 0, 0, 0, 0]
            print("[Control] Control started.")
        else:
            if len(state) == 6:
                self.move(state)
            elif len(state) == 7:
                self.moveq(state)
            if trigger is not None:
                self.set_gripper(trigger)

    def stop_control(self):
        if self.is_controlling:
            self.is_controlling = False
            self.arm_first_state = None
            self.prev_tech_state = None
            print("[Control] Control stopped.")

    def move(self, tech_state):
        # 计算手柄在世界坐标系中的位移增量
        delta_x = tech_state[0] - self.prev_tech_state[0]
        delta_y = tech_state[1] - self.prev_tech_state[1]
        delta_z = tech_state[2] - self.prev_tech_state[2]
        
        # 获取手柄的姿态欧拉角（弧度）
        # 假设顺序为 [x, y, z, rx, ry, rz]
        controller_roll = self.prev_tech_state[3]
        controller_pitch = self.prev_tech_state[4]
        controller_yaw = self.prev_tech_state[5]
        
        # 创建绕Z-Y-X轴的旋转矩阵（ZYX约定）
        # 先绕X轴旋转(roll)，再绕Y轴旋转(pitch)，最后绕Z轴旋转(yaw)
        R_controller = np.array([
            [np.cos(controller_yaw)*np.cos(controller_pitch),
             np.cos(controller_yaw)*np.sin(controller_pitch)*np.sin(controller_roll) - np.sin(controller_yaw)*np.cos(controller_roll),
             np.cos(controller_yaw)*np.sin(controller_pitch)*np.cos(controller_roll) + np.sin(controller_yaw)*np.sin(controller_roll)],
            [np.sin(controller_yaw)*np.cos(controller_pitch),
             np.sin(controller_yaw)*np.sin(controller_pitch)*np.sin(controller_roll) + np.cos(controller_yaw)*np.cos(controller_roll),
             np.sin(controller_yaw)*np.sin(controller_pitch)*np.cos(controller_roll) - np.cos(controller_yaw)*np.sin(controller_roll)],
            [-np.sin(controller_pitch),
             np.cos(controller_pitch)*np.sin(controller_roll),
             np.cos(controller_pitch)*np.cos(controller_roll)]
        ])
        
        # 第一步：将世界坐标系中的位移转换到手柄的局部坐标系中
        # 这里使用旋转矩阵的转置（等于逆矩阵）来进行坐标变换
        tech_delta = R_controller.T @ np.array([delta_x, delta_y, delta_z])
        tech_delta_x, tech_delta_y, tech_delta_z = tech_delta
        
        
        
        # 获取机械臂基座的姿态欧拉角
        arm_base_roll = self.arm_first_state[3]
        arm_base_pitch = self.arm_first_state[4]
        arm_base_yaw = self.arm_first_state[5]
        
        # 创建机械臂基座的旋转矩阵
        R_arm_base = np.array([
            [np.cos(arm_base_yaw)*np.cos(arm_base_pitch),
             np.cos(arm_base_yaw)*np.sin(arm_base_pitch)*np.sin(arm_base_roll) - np.sin(arm_base_yaw)*np.cos(arm_base_roll),
             np.cos(arm_base_yaw)*np.sin(arm_base_pitch)*np.cos(arm_base_roll) + np.sin(arm_base_yaw)*np.sin(arm_base_roll)],
            [np.sin(arm_base_yaw)*np.cos(arm_base_pitch),
             np.sin(arm_base_yaw)*np.sin(arm_base_pitch)*np.sin(arm_base_roll) + np.cos(arm_base_yaw)*np.cos(arm_base_roll),
             np.sin(arm_base_yaw)*np.sin(arm_base_pitch)*np.cos(arm_base_roll) - np.cos(arm_base_yaw)*np.sin(arm_base_roll)],
            [-np.sin(arm_base_pitch),
             np.cos(arm_base_pitch)*np.sin(arm_base_roll),
             np.cos(arm_base_pitch)*np.cos(arm_base_roll)]
        ])
        
        # 第二步：将手柄局部坐标系中的位移增量转换到机械臂末端坐标系中
        # 这里使用手柄的旋转矩阵进行变换
        arm_delta = R_arm_base @ np.array([tech_delta_x, tech_delta_y, tech_delta_z])
        arm_delta_x, arm_delta_y, arm_delta_z = arm_delta
        
        # 应用转换后的位移增量到机械臂基座坐标系中
        next_state = [
            self.arm_first_state[0] + arm_delta_x,
            self.arm_first_state[1] + arm_delta_y,
            self.arm_first_state[2] + arm_delta_z,
            self.arm_first_state[3] + (tech_state[3] - self.prev_tech_state[3]),
            self.arm_first_state[4] + (tech_state[4] - self.prev_tech_state[4]),
            self.arm_first_state[5] + (tech_state[5] - self.prev_tech_state[5])
        ]
        
        success = self.arm_controller.rm_movep_canfd(next_state, False, 0, 80)

    def moveq(self, tech_state):
        """四元数使用绝对姿态"""

        self.delta[0] = tech_state[0] - self.prev_tech_state[0]
        self.delta[1] = tech_state[1] - self.prev_tech_state[1]
        self.delta[2] = tech_state[2] - self.prev_tech_state[2]
        self.delta[3] = tech_state[3] - self.prev_tech_state[3]
        self.delta[4] = tech_state[4] - self.prev_tech_state[4]
        self.delta[5] = tech_state[5] - self.prev_tech_state[5]
        self.delta[6] = tech_state[6] - self.prev_tech_state[6]
        
        next_state = [
            self.arm_first_state[0] + self.delta[0],  
            self.arm_first_state[1] + self.delta[1], 
            self.arm_first_state[2] + self.delta[2], 
            self.delta[3],
            self.delta[4],
            self.delta[5],
            self.delta[6]
        ] 
        
        success = self.arm_controller.rm_movep_canfd(next_state, False, 0, 80)

    def move_init(self, state):
        return self.arm_controller.rm_movej(state, 20, 0, 0, 1)
        
    def set_gripper(self, gripper):
        if gripper < 0.20 and not self.gripper_close:
            success = self.arm_controller.rm_set_gripper_pick(500, 1000, True, 0)
            self.gripper_close = True
        elif gripper > 0.8 and self.gripper_close:
            success = self.arm_controller.rm_set_gripper_release(500, True, 0)        
            self.gripper_close = False
        # if self.get_gripper() and self.get_gripper().get('mode') in [1, 2, 3]:
        #     def gripper_operation(controller, position):
        #         controller.rm_set_gripper_position(position, False, 1)
                
            
        #     # 计算目标位置
        #     target_position = int(gripper * 1000)
            
        #     # 创建并启动线程
        #     gripper_thread = threading.Thread(
        #         target=gripper_operation,
        #         args=(self.arm_controller, target_position)
        #     )
        #     gripper_thread.start()
        #     print(f"Set gripper to {target_position/1000}")  # 转换回原始单位显示
        # else:
        #     print("Gripper is not in position control mode.")

        
        

    def __del__(self):
        try:
            # 停止轮询线程
            if self.polling_thread is not None:
                self.polling_thread.join()
                self.polling_thread = None
            
            if hasattr(self, 'arm_controller'):
                # 可能的其他清理操作
                pass
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

if __name__ == '__main__':
    rm_ip = "192.168.0.18"
    left = RM_controller(rm_ip,port = 8080)
    try:
        left.start()
    except Exception as e:
        print(f"Failed to start robot arm: {e}")
    # 主线程可以做其他事，或保持运行
    try:
        while True:
            print(left.get_state())
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("退出")