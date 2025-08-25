import sys
import socket
import threading
import json
from RealMan import RM_controller
from Robotic_Arm.rm_robot_interface import *
import os
import time
import math
from scipy.spatial.transform import Rotation as R  # 需要安装 scipy

# Socket 配置
HOST = '192.168.0.20'  # 替换为服务器 IP 地址
PORT = 12345            # 替换为服务器端口号

class Teleoperation:
    def __init__(self):
        # 初始化机械臂控制器
        self.left_wrist_controller = RM_controller("192.168.0.18", rm_thread_mode_e.RM_TRIPLE_MODE_E)
        self.right_wrist_controller = RM_controller("192.168.0.19", rm_thread_mode_e.RM_TRIPLE_MODE_E)
        debug_print("机械臂初始化完成", True)

        # 初始化 socket 连接
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))
        debug_print(f"已连接到 Unity 服务器 {HOST}:{PORT}", True)

        # 多线程
        self.sender_thread = threading.Thread(target=self.feedback_thread_func, args=(self.sock,), daemon=True)
        self.receiver_thread = threading.Thread(target=self.socket_receiver, daemon=True)
        self.collect_thread = threading.Thread(target=self.data_collect_thread, daemon=True)
        

    def run(self):
        self.sender_thread.start()
        self.receiver_thread.start()
        self.collect_thread.start()
        while True:
            time.sleep(1)
            # self.sender_thread.join(1)
            # self.receiver_thread.join(1)

    def data_collect_thread(self):
        """
        数据收集线程，定期收集机械臂数据并保存
        """
        while True:
            try:
                # 这里可以添加数据收集和保存的逻辑
                time.sleep(1)  # 每秒收集一次数据
            except Exception as e:
                debug_print(f"数据收集线程出错: {e}", True)
                break

    def feedback_thread_func(self, sock ,delay = 0.05):
        while True:
            try:
                # 读取当前位置并反馈
                left_state = self.left_wrist_controller.get_state()
                right_state = self.right_wrist_controller.get_state()
                left_quat = euler_to_quat(left_state[3], left_state[4], left_state[5])
                right_quat = euler_to_quat(right_state[3], right_state[4], right_state[5])
                
                feedback = {
                    "leftPos":{
                        "x": left_state[0],
                        "y": left_state[1],
                        "z": left_state[2],
                    },
                    "leftRot":{
                        "x": left_state[3]*180/math.pi,
                        "y": left_state[4]*180/math.pi,
                        "z": left_state[5]*180/math.pi,
                    },
                    "leftQuat": left_quat,
                    "rightPos":{
                        "x": right_state[0],
                        "y": right_state[1],
                        "z": right_state[2],
                    },
                    "rightRot":{
                        "x": right_state[3]*180/math.pi,
                        "y": right_state[4]*180/math.pi,
                        "z": right_state[5]*180/math.pi,
                    },
                    "rightQuat": right_quat
                }
                feedback_json = json.dumps(feedback) + "\n"
                sock.sendall(feedback_json.encode("utf-8"))
                time.sleep(delay)
            except KeyboardInterrupt:
                break

    def handle_socket_data(self,data_dict):
        """
        处理从 socket 接收到的数据
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
                    self.left_wrist_controller.start_control([x_l, y_l, z_l, roll_l, pitch_l, yaw_l],left_trigger)
                else:
                    self.left_wrist_controller.stop_control()
                        

            
            if x_r == 0 and y_r == 0 and z_r == 0:
                debug_print("右手坐标为0，丢弃该条信息", True)
            else:
                if data_dict['rightGrip']==True:
                    self.right_wrist_controller.start_control([x_r, y_r, z_r, roll_r, pitch_r, yaw_r],right_trigger)
                else:
                    self.right_wrist_controller.stop_control()


        except Exception as e:
            debug_print(f"处理数据时出错: {e}", True)



    def socket_receiver(self):
        """
        Socket 接收线程
        """
        buffer = ""
        while True:
            try:
                data = self.sock.recv(1024)
                if not data:
                    debug_print("[Quest断开连接]")
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip() == "":
                        continue
                    try:
                        msg = json.loads(line)
                        self.handle_socket_data(msg)
                    except json.JSONDecodeError as e:
                        debug_print("[JSON解析失败]", e)
                        break
            except Exception as e:
                debug_print(f"Socket接收异常: {e}", True)
                break

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

if __name__ == '__main__':
    operate = Teleoperation()
    try:
        operate.run()
    except KeyboardInterrupt:
        print("\n[退出] 检测到 Ctrl+C，程序已终止。")
        if hasattr(operate, "sock"):
            operate.sock.close()
