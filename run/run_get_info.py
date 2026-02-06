import sys, os, time, threading
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from EasyTeleop.Components import TeleopMiddleware, DataCollect
from EasyTeleop.Device.Robot.RealManWithIK import RealManWithIK
from EasyTeleop.Device.Camera.RealSenseCamera import RealSenseCamera

# 去掉与 TRRO 相关的导入
# from EasyTeleop.Device.VR.TrroFieldVR_Reflect import TrroFieldVR

# 如果你愿意，也可以从模块里导入 MSG_DATA；若没有就用 0
try:
    from EasyTeleop.Device.VR.TrroFieldVR_Reflect import MSG_DATA
except Exception:
    MSG_DATA = 0  # 和现场端定义一致：MSG_DATA = 0


if __name__ == '__main__':
    try:
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
        log_file_path = os.path.join(output_dir, "1.txt")

        try:
            RealSenseCamera.find_device()
        except Exception as _:
            print("RealSense 未检测到，忽略此步或自行处理。")

        # 业务组件
        dc = DataCollect()
        l_arm = RealManWithIK({"ip": "192.168.0.18", "port": 8080})
        r_arm = RealManWithIK({"ip": "192.168.0.19", "port": 8080})
        teleop = TeleopMiddleware()

        # 如果还要本地 Realsense 采集用于你们的 UI/记录，保留；否则可注释
        # camera1 = RealSenseCamera({"serial": "153122070447", "target_fps": 30})

        current_script_path = os.path.abspath(__file__)
        current_script_dir = os.path.dirname(current_script_path)

        devices = [l_arm, r_arm]


        l_arm.on("state", dc.put_robot_state)

        teleop.on("leftGripTurnDown", l_arm.start_control)
        teleop.on("leftGripTurnUp",   l_arm.stop_control)
        teleop.on("leftPosRot",       l_arm.add_pose_data)

        teleop.on("rightGripTurnDown", r_arm.start_control)
        teleop.on("rightGripTurnUp",   r_arm.stop_control)
        teleop.on("rightPosRot",       r_arm.add_pose_data)

        teleop.on("buttonATurnDown", dc.toggle_capture_state)

        def handle_from_remote(msg):
            # 打印接受到的消息
            print("Received message:", msg)

            try:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                msg_str = str(msg)
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] {msg_str}\n")
                    f.flush()
            except Exception as e:
                print(f"写入 1.txt 失败: {e}")

        # ===== 机器人真实数据 → 在本地输出 =====

        def robot_state_loop():
            """
            外部线程：周期性读取左右臂的真实状态，并在本地输出。
            不修改 TrroFieldVR 内部代码。
            """
            ROBOT_SEND_HZ = 50  # 你可以根据带宽/需求调整，比如 30 或 60
            period = 1.0 / max(1, ROBOT_SEND_HZ)

            while True:
                t0 = time.monotonic()
                try:
                    # 左臂
                    try:
                        pose_l   = l_arm.get_pose_data() or []
                        ee_l     = l_arm.get_end_effector_data() or []
                        joints_l = l_arm.get_joint_data() or []

                        msg_l = {
                            "type": "robot_state",
                            "payload": {
                                "arm": "left",
                                "pose": pose_l,
                                "end_effector": ee_l,
                                "joints": joints_l,
                            }
                        }
                        # 在本地输出数据
                        print("Left Arm State:", msg_l)

                    except Exception as e:
                        print(f"[robot_state_loop] left arm output failed: {e}")

                    # 右臂（如无需上传可注释这一块）
                    try:
                        pose_r   = r_arm.get_pose_data() or []
                        ee_r     = r_arm.get_end_effector_data() or []
                        joints_r = r_arm.get_joint_data() or []

                        msg_r = {
                            "type": "robot_state",
                            "payload": {
                                "arm": "right",
                                "pose": pose_r,
                                "end_effector": ee_r,
                                "joints": joints_r,
                            }
                        }
                        # 在本地输出数据
                        print("Right Arm State:", msg_r)

                    except Exception as e:
                        print(f"[robot_state_loop] right arm output failed: {e}")

                except Exception as e:
                    print(f"[robot_state_loop] unexpected error: {e}")

                dt = time.monotonic() - t0
                if dt < period:
                    time.sleep(period - dt)

        # ===== 启动顺序 =====
        l_arm.start()
        r_arm.start()

        # 启动机器人状态输出线程（外部线程）
        threading.Thread(target=robot_state_loop, daemon=True).start()

        # ===== 主循环 =====
        while True:
            states = [d.get_conn_status() for d in devices if hasattr(d, "get_conn_status")]
            print(f"设备连接状态: {states}")
            time.sleep(1)

    except KeyboardInterrupt:
        print("用户中断，退出程序。")
        sys.exit(0)
    except Exception as e:
        print(f"初始化失败: {e}")
        sys.exit(1)
