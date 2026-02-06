import time
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from EasyTeleop.TeleopGroup import TwoArmWithTriggerTeleopGroup
from EasyTeleop.Device.Robot import RealManWithIK
from EasyTeleop.Device.VR.TrroFieldVR_Reflect import TrroFieldVR
from EasyTeleop.Device.Camera.TestCamera import TestCamera
from EasyTeleop.Device.Camera.RealSenseCamera import RealSenseCamera


if __name__ == "__main__":
    try:
        # List connected RealSense devices to help choose the right serials
        # RealSenseCamera.find_device()

        left_arm = RealManWithIK({"ip": "192.168.0.18", "port": 8080})
        right_arm = RealManWithIK({"ip": "192.168.0.19", "port": 8080})
        CFG = "./src/trro-gateway-sdk-x64-release/config.json"
        LIB = "./src/trro-gateway-sdk-x64-release/sdk_lib/libtrro_field.so"

        vr = TrroFieldVR({
            "lib_path": LIB,
            "config_path": CFG,
            "enable_data_pump": False,
            "send_hz": 100
        })
        @vr.on("message")
        def debug(msg):
            print("[RX]", msg)

        # vr = TrroFieldVR({"ip": "192.168.0.103", "port": 12345})

        # cam1 = RealSenseCamera({"serial": "153122070447", "target_fps": 30})
        cam2 = RealSenseCamera({"serial": "427622270438", "target_fps": 15})
        # cam3 = RealSenseCamera({"serial": "427622270277", "target_fps": 15})
        cam1 = TestCamera({"fps": 30})
        # cam2 = TestCamera({"fps": 30})
        cam3 = TestCamera({"fps": 30})
        

        teleop_group = TwoArmWithTriggerTeleopGroup(
            [left_arm, right_arm, vr, cam1, cam2, cam3]
        )

        @teleop_group.on("status_change")
        def teleop_status(state):
            # 1 = running, 0 = stopped
            print(f"Teleop group status: {state}")

        @teleop_group.data_collect.on("status_change")
        def collect_status(state):
            # 1 = capturing, 0 = idle
            print(f"Data capture status: {state}")

        if not teleop_group.start():
            raise RuntimeError("Failed to start TwoArmWithTriggerTeleopGroup")

        while True:
            connect_states = [
                device.get_conn_status() if device else None
                for device in teleop_group.devices
            ]
            print(f"Device connection states: {connect_states}")
            time.sleep(1)
    except Exception as e:
        print(f"Initialization failed: {e}")
