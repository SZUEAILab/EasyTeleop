from Robotic_Arm.rm_robot_interface import *
import time
import numpy as np
import threading
from threading import Lock

class RM_controller:
    def __init__(self, rm_ip, thread_mode=None, poll_interval=0.01):  # 添加了轮询间隔参数
        try:
            self.arm_controller = RoboticArm(thread_mode)
            self.handle = self.arm_controller.rm_create_robot_arm(rm_ip, 8080) 
        except Exception as e:
            raise ConnectionError(f"Failed to initialize robot arm: {str(e)}")
        
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
        
        # 启动轮询线程
        self.start_polling()

        print("[Initialize]Robot arm initialized and polling started.")
        
        # 等待初始状态被获取
        while self.current_state is None:
            print("Waiting for initial state...")
            time.sleep(0.1)

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
        """轮询状态的内部方法，在单独线程中运行"""
        while self.polling_running:
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
    
    def move(self, tech_state):
        # 使用缓存的当前状态，不再重新查询
        with self.state_lock:
            current_state = self.current_state
            
        if self.prev_tech_state is None:
            self.prev_tech_state = tech_state
            return
            
        if self.arm_first_state is None:
            self.arm_first_state = current_state
            return
         
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

    def move_init(self, state):
        return self.arm_controller.rm_movej(state, 20, 0, 0, 1)
        
    def set_gripper(self, gripper):
        if gripper < 0.20 and not self.gripper_close:
            success = self.arm_controller.rm_set_gripper_pick(500, 1000, True, 0)
            self.gripper_close = True
        elif gripper > 0.8 and self.gripper_close:
            success = self.arm_controller.rm_set_gripper_release(500, True, 0)        
            self.gripper_close = False

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
    left = RM_controller(rm_ip, rm_thread_mode_e.RM_TRIPLE_MODE_E)
    while True:
        print(left.get_gripper())
        time.sleep(0.1)