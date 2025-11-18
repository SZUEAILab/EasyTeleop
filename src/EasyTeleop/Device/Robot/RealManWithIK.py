from Robotic_Arm.rm_robot_interface import rm_thread_mode_e, RoboticArm
import time
import numpy as np
import threading
from threading import Lock
from typing import Dict, Any
from collections import deque
from .BaseRobot import BaseRobot
from .Realman_IK.ik_qp import QPIK
# from .Realman_IK.ik_rbtdef import *
# from .Realman_IK.ik_rbtutils import *

def pose_to_matrix(x, y, z, roll, pitch, yaw):
    Rz = np.array([
        [np.cos(yaw), -np.sin(yaw), 0],
        [np.sin(yaw),  np.cos(yaw), 0],
        [0,            0,           1]
    ])
    Ry = np.array([
        [ np.cos(pitch), 0, np.sin(pitch)],
        [ 0,             1, 0],
        [-np.sin(pitch), 0, np.cos(pitch)]
    ])
    Rx = np.array([
        [1, 0,            0],
        [0, np.cos(roll), -np.sin(roll)],
        [0, np.sin(roll),  np.cos(roll)]
    ])
    R = Rz @ Ry @ Rx  # 旋转矩阵

    # 齐次变换矩阵
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = [x, y, z]
    return T

class RealManWithIK(BaseRobot):
    """
    RealMan机器人控制器，继承自Robot基类，实现具体控制逻辑。
    """
    # 定义需要的配置字段为静态字段
    name = "睿尔曼R75b机械臂"
    description = "用于控制RealMan机械臂的机器人控制器"
    need_config = {
        "ip": {
            "type": "string",
            "description": "睿尔曼机械臂IP地址",
            "default": "192.168.1.18"
        },
        "port": {
            "type": "integer",
            "description": "睿尔曼机械臂端口号",
            "default": 8080
        },
    }
    
    def __init__(self, config: Dict[str, Any]):
        
        self.ip = None
        self.port = None
        
        super().__init__(config)
        
        self.target_fps = 30  # 目标帧率
        self.min_interval = 1.0 / self.target_fps  # 最小间隔时间
        
        self.arm_controller = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)
        
        # 控制相关变量
        self.is_controlling = False
        self.prev_tech_state = None
        self.arm_first_state = None
        self.gripper_close = False
        self.delta = None

        self.q_last = None

        self.dT = 0.02

        self.ik = QPIK("RM75B", self.dT)
        
        
    

    def _main(self):
        try:
            last_time = time.time()
            succ, arm_state = self.arm_controller.rm_get_current_arm_state()
            if not succ:
                self.current_pose_data = arm_state["pose"]
                self.current_joint_data = arm_state["joint"]
                self.emit("pose",self.current_pose_data)#调用回调函数
                self.emit("joint",self.current_joint_data)#调用回调函数
            else:
                raise RuntimeError("Failed to get arm state")

        
            # 获取夹爪状态
            succ_gripper, gripper_state = self.arm_controller.rm_get_gripper_state()
            if not succ_gripper:
                self.current_end_effector_data = gripper_state['actpos']
                self.emit("end_effector",[self.current_end_effector_data])#调用回调函数
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
                
    def _connect_device(self) -> bool:
        try:
            self.handle = self.arm_controller.rm_create_robot_arm(self.ip, self.port) 
            if self.handle.id == -1:
                raise ConnectionError(f"Failed to connect to robot arm at {self.ip}:{self.port}")
            print(f"[Initialize]Robot arm connected at {self.ip}:{self.port}")

            # 获取手臂状态
            succ, arm_state = self.arm_controller.rm_get_current_arm_state()
            # print(arm_state)
            if not succ:
                self.current_pose_data = arm_state["pose"]
                self.current_joint_data = arm_state["joint"]
            else:
                raise RuntimeError("Failed to get arm state")
            
            # 获取夹爪状态
            succ_gripper, gripper_state = self.arm_controller.rm_get_gripper_state()
            if not succ_gripper:
                self.current_end_effector_data = gripper_state
            else:
                raise RuntimeError("Failed to get gripper state")
            
            self.setik()
                    
            return True
            
        except Exception as e:
            self.arm_controller.rm_delete_robot_arm()
            return False
        
    def setik(self):
        try:
            tool_frame = self.arm_controller.rm_get_current_tool_frame()[1]['pose']
            world_frame = self.arm_controller.rm_get_current_work_frame()[1]['pose']
            install_angel = self.arm_controller.rm_get_install_pose()
            self.ik.set_install_angle([install_angel['x'], install_angel['y'], install_angel['z']], 'deg')
            self.ik.set_work_cs_params(world_frame)
            self.ik.set_tool_cs_params(tool_frame)
            # self.ik.set_7dof_elbow_min_angle(3, 'deg')
            # self.ik.set_7dof_q3_min_angle(-30, 'deg')
            # self.ik.set_7dof_q3_max_angle(30, 'deg')
            self.ik.set_dq_max_weight([1.0, 1.0, 1.0, 1.0, 0.1, 1.0, 1.0])
        except Exception as e:
            print(f"Error setting IK parameters: {str(e)}") 
    
    def _disconnect_device(self) -> bool:
        """
        断开与机械臂的连接
        :return: 是否成功断开连接
        """
        try:
            
            # 断开机械臂连接
            if self.arm_controller is not None and self.handle is not None:
                # 调用SDK接口断开连接
                self.arm_controller.rm_delete_robot_arm()
                self.handle = None
            
            print(f"[Disconnect] Robot arm disconnected from {self.ip}:{self.port}")
            return True
            
        except Exception as e:
            print(f"Error disconnecting robot arm: {str(e)}")
            return False

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
    def get_pose_data(self):
        """获取当前状态（线程安全）"""
        return self.current_pose_data.copy() if self.current_pose_data is not None else None

    
    def start_control(self, state=None, trigger=None):
        """开始控制手臂，启动控制线程"""
        if not self.is_controlling:
            self.is_controlling = True
            self.control_thread_running = True
            
            # 启动控制线程
            self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
            self.control_thread.start()
            
            print("[Control] Control started.")

    def stop_control(self):
        """停止控制手臂"""
        if self.is_controlling:
            self.is_controlling = False
            self.control_thread_running = False
            
            # 等待控制线程结束
            if self.control_thread and self.control_thread.is_alive():
                self.control_thread.join(timeout=1.0)

            # 清空队列
            self.pose_queue.clear()
            self.end_effector_queue.clear()
            
            self.arm_first_state = None
            self.prev_tech_state = None
            print("[Control] Control stopped.")
    def _control_loop(self):
        """控制线程主循环"""
        while self.control_thread_running:
            control_start = time.time()
            # 处理位姿队列，只取最新的一帧数据
            pose_data = None
            if self.pose_queue:
                pose_data = self.pose_queue[-1]  # 获取最新数据但不移除
            
            # 只处理最新的位姿数据
            if pose_data is not None:
                if self.prev_tech_state is None:
                    # 初始化状态
                    self.prev_tech_state = pose_data
                    self.arm_first_state = self.get_pose_data()
                    self.q_last = np.deg2rad(self.get_joint_data())
                    print(self.q_last)
                    self.delta = [0, 0, 0, 0, 0, 0, 0]
                else:
                    
                    # 执行位姿控制
                    if len(pose_data) == 6:
                        self.movej(pose_data)
                    elif len(pose_data) == 7:
                        self.moveq(pose_data)
            
            # 处理夹爪队列，只取最新的一帧数据
            gripper_data = None
            if self.end_effector_queue:
                gripper_data = self.end_effector_queue[-1]  # 获取最新数据但不移除
            
            # 只处理最新的夹爪数据
            if gripper_data is not None:
                self.set_gripper(gripper_data)
            
            control_end = time.time()
            # print(control_end - control_start)
            control_sleep = self.dT - (control_end - control_start)
            if control_sleep > 0:
                time.sleep(control_sleep)

    def move(self, tech_state):
        """欧拉角控制"""
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

    def movej(self, tech_state):
        """欧拉角控制"""
        for i in range(6):
            self.delta[i] = tech_state[i] - self.prev_tech_state[i]
        # self.prev_tech_state = tech_state.copy()
        hand_x = self.arm_first_state[0] + self.delta[0]
        hand_y = self.arm_first_state[1] + self.delta[1]
        hand_z = self.arm_first_state[2] + self.delta[2]
        hand_roll = self.arm_first_state[3] + self.delta[3]
        hand_pitch = self.arm_first_state[4] + self.delta[4]
        hand_yaw = self.arm_first_state[5] + self.delta[5]

        # x, y, z, roll, pitch, yaw = self.hand_to_base_transform(
        #     hand_x, hand_y, hand_z, hand_roll, hand_pitch, hand_yaw
        # )
        # x, y, z, roll, pitch, yaw = tech_state
        # Td = pose_to_matrix(x, y, z, roll, pitch, yaw)
        Td = pose_to_matrix(hand_x, hand_y, hand_z, hand_roll, hand_pitch, hand_yaw)
        # print("!!!!!!!!!!!!!!!!!1self.q_last:", self.q_last)
        q_solve = self.ik.sovler(self.q_last,Td)

        # 计算 FK，检查误差
        T_check = self.ik.fkine(q_solve)
        pos_err = np.linalg.norm(Td[:3, 3] - T_check[:3, 3]) * 1000  # mm
        cos_angle = (np.trace(Td[:3, :3].T @ T_check[:3, :3]) - 1) / 2
        cos_angle = np.clip(cos_angle, -1.0, 1.0)  # 避免数值误差
        rot_err = np.degrees(np.arccos(cos_angle))

        # 打印调试信息
        # print("输入 tech_state:", tech_state)
        # print("q_last (deg):", np.degrees(self.q_last))
        # print("q_solve (deg):", np.degrees(q_solve))
        # print("Δq (deg):", np.degrees(q_solve - self.q_last))
        # print(f"位置误差: {pos_err:.3f} mm, 姿态误差: {rot_err:.3f} °")
        # print(f"姿态误差: {rot_err:.3f} °")

        # 误差检查
        # if pos_err > 10 or rot_err > 5:
        #     print("[WARN] IK 未收敛，忽略本次指令")
        #     return
        
        self.q_last = q_solve
        self.arm_controller.rm_movej_canfd(np.degrees(q_solve).tolist(),False,0,0,50)
    def moveRemote(self, tech_state):
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