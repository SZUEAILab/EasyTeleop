from Robotic_Arm.rm_robot_interface import *
import time
import numpy as np
import threading
from threading import Lock
from .Robot import Robot

class RM_controller(Robot):
    """
    RealMan机器人控制器，继承自Robot基类，实现具体控制逻辑。
    """
    def __init__(self, config, thread_mode=rm_thread_mode_e.RM_TRIPLE_MODE_E, poll_interval=0.01):
        super().__init__(config)
        self.ip = config["ip"]
        self.port = int(config["port"])
        self.thread_mode = thread_mode
        
        
        # 状态存储变量
        self.current_state = None
        self.current_gripper_state = None
        
        # 线程相关变量
        self.poll_interval = poll_interval  # 轮询间隔（秒）
        self.polling_thread = None
        self.polling_running = False
        self.state_lock = Lock()  # 用于线程安全访问状态变量
        
        # 原有变量
        self.is_controlling = False
        self.prev_tech_state = None
        self.arm_first_state = None
        self.gripper_close = False
        self.delta = [0, 0, 0 , 0 , 0 , 0]
        
        
        
    def start(self):
        try:
            self.arm_controller = RoboticArm(self.thread_mode)
            self.handle = self.arm_controller.rm_create_robot_arm(self.ip, self.port) 
            if self.handle.id == -1:
                raise ConnectionError(f"Failed to connect to robot arm at {self.ip}:{self.port}")
            print(f"[Initialize]Robot arm connected at {self.ip}:{self.port}")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize robot arm: {str(e)}")
        # 启动轮询线程
        self.start_polling()

        print("[Initialize]Robot arm initialized and polling started.")
        
        # 获取初始状态
        try:
            # 获取手臂状态
            succ, arm_state = self.arm_controller.rm_get_current_arm_state()
            if not succ:
                with self.state_lock:
                    self.current_state = arm_state["pose"]
            
            # 获取夹爪状态
            succ_gripper, gripper_state = self.arm_controller.rm_get_gripper_state()
            if not succ_gripper:
                with self.state_lock:
                    self.current_gripper_state = gripper_state
            
        except Exception as e:
            self.stop_polling()
            raise RuntimeError(f"Failed to get initial robot state: {str(e)}")

    def start_polling(self):
        """启动状态轮询线程"""
        if not self.polling_running:
            self.polling_running = True
            self.polling_thread = threading.Thread(target=self._poll_state, daemon=True)
            self.polling_thread.start()

    def stop_polling(self):
        """停止状态轮询线程"""
        self.polling_running = False
        if self.polling_thread is not None:
            self.polling_thread.join()
            self.polling_thread = None

    def _poll_state(self):
        while self.polling_running:
            try:
                succ, arm_state = self.arm_controller.rm_get_current_arm_state()
                if not succ:
                    with self.state_lock:
                        self.current_state = arm_state["pose"]
                        self.emit("state",self.current_state)#调用回调函数
            
                # 获取夹爪状态
                succ_gripper, gripper_state = self.arm_controller.rm_get_gripper_state()
                if not succ_gripper:
                    with self.state_lock:
                        self.current_gripper_state = gripper_state
                
            except Exception as e:
                print(f"Error polling robot state: {str(e)}")
                break
            
            time.sleep(self.poll_interval)

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
         
        self.delta[0] = tech_state[0] - self.prev_tech_state[0]
        self.delta[1] = tech_state[1] - self.prev_tech_state[1]
        self.delta[2] = tech_state[2] - self.prev_tech_state[2]
        self.delta[3] = tech_state[3] - self.prev_tech_state[3]
        self.delta[4] = tech_state[4] - self.prev_tech_state[4]
        self.delta[5] = tech_state[5] - self.prev_tech_state[5]
        
        next_state = [
            self.arm_first_state[0] + self.delta[0],  
            self.arm_first_state[1] + self.delta[1], 
            self.arm_first_state[2] + self.delta[2], 
            self.arm_first_state[3] + self.delta[3],
            self.arm_first_state[4] + self.delta[4],
            self.arm_first_state[5] + self.delta[5]
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
            self.stop_polling()
            
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