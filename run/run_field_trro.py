# app_demo/run_field_trro.py
import sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from EasyTeleop.Components import TeleopMiddleware, DataCollect
from EasyTeleop.Device.Robot.RealManWithIK import RealManWithIK
from EasyTeleop.Device.Camera.RealSenseCamera import RealSenseCamera

# ★ 用 TRRO 现场端设备类，替代原来的 VRSocket
from EasyTeleop.Device.VR.TrroFieldVR_Reflect import TrroFieldVR

if __name__ == '__main__':
    try:
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
        log_file_path = os.path.join(output_dir, "1.txt")
        # （可选）相机检测
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

        # current_script_path = os.path.abspath(__file__)
        # current_script_dir = os.path.dirname(current_script_path)

        # # 构建 third-party 目录的路径（相对当前脚本目录：../third-party/）
        # third_party_dir = os.path.join(current_script_dir, "../third-party/trro-gateway-sdk-x64-release/")
        # # 规范化路径（处理 ../ 等相对路径符号）
        # third_party_dir = os.path.normpath(third_party_dir)

        # # 构建配置文件和库文件的相对路径
        # CFG = os.path.join(third_party_dir, "config.json")
        # LIB = os.path.join(third_party_dir, "sdk_lib/libtrro_field.so")
        # ★★ 关键：创建 TRRO 现场端设备
        # 路径可不传，类里默认就是 third-party/trro-gateway-sdk-x64-release 下的 so/config.json
        CFG = "./src/trro-gateway-sdk-x64-release/config.json"
        LIB = "./src/trro-gateway-sdk-x64-release/sdk_lib/libtrro_field.so"

        field_vr = TrroFieldVR({
            "lib_path": LIB,
            "config_path": CFG,
            "enable_data_pump": False,
            "send_hz": 100
        })

        devices = [l_arm, r_arm, field_vr]

        # ===== 事件对接（保持你原来的逻辑不变）=====
        

        l_arm.on("state", dc.put_robot_state)

        teleop.on("leftGripTurnDown", l_arm.start_control)
        teleop.on("leftGripTurnUp",   l_arm.stop_control)
        teleop.on("leftPosRot",       l_arm.add_pose_data)

        teleop.on("rightGripTurnDown", r_arm.start_control)
        teleop.on("rightGripTurnUp",   r_arm.stop_control)
        teleop.on("rightPosRot",       r_arm.add_pose_data)

        teleop.on("buttonATurnDown", dc.toggle_capture_state)

        # ★★ 用 TRRO 设备的“message”事件喂给中间件（替代 VRSocket.on("message", ...)）
        @field_vr.on("message")
        def handle_from_remote(msg):
            # 现场端收到远端的 JSON 指令（或带 raw 的二进制包）
            # 你的 TeleopMiddleware 之前就是吃 VRSocket 的消息，这里保持一致
            print("TRRO:", msg)
            teleop.handle_socket_data(msg)
            try:
                # 获取当前时间戳（格式：年-月-日 时:分:秒）
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                # 将 msg 转为字符串（支持字典、二进制等类型）
                msg_str = str(msg)
                # 追加写入文件（每行格式：时间戳 + 消息内容）
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] {msg_str}\n")
                    # 可选：每写一条刷新一次缓冲区，确保即时保存（避免程序崩溃丢失数据）
                    f.flush()
            except Exception as e:
                print(f"写入 1.txt 失败: {e}")

        # ===== 启动顺序 =====
        # dc.start()
        # camera1.start()  # 如果你要同时跑本地相机数据，就启用

        l_arm.start()
        r_arm.start()

        # ★ 启动 TRRO 现场端设备（内部会自动 init/start SDK、起多路视频线程、起数据/统计线程）
        field_vr.start()

        # ===== 主循环 =====
        while True:
            states = [d.get_conn_status() for d in devices if hasattr(d, "get_conn_status")]
            print(f"设备连接状态: {states}")
            time.sleep(1)

    except Exception as e:
        print(f"初始化失败: {e}")
        sys.exit(1)
