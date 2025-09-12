from TeleopMiddleware import TeleopMiddleware
class TeleopGroup:
    def __init__(self, group_id, config):
        self.id = group_id
        self.config = config
        self.teleop = None
        self.running = False

    def start(self):
        # 按照配置引用device_pool
        self.teleop = Teleoperation()
        print(self.config)
        # 左手臂
        left_id = self.config.get('left_arm')
        if isinstance(left_id, str) and left_id.isdigit():
            left_id = int(left_id)
        self.left_arm = device_pool['arm'].get(left_id)
        if self.left_arm:
            self.teleop.on("leftGripDown", self.left_arm.start_control)
            self.teleop.on("leftGripUp", self.left_arm.stop_control)
        # 右手臂
        right_id = (self.config.get('right_arm'))
        if isinstance(right_id, str) and right_id.isdigit():
            right_id = int(right_id)
        self.right_arm = device_pool['arm'].get(right_id)
        if self.right_arm:
            self.teleop.on("rightGripDown", self.right_arm.start_control)
            self.teleop.on("rightGripUp", self.right_arm.stop_control)
        # VR头显
        vr_id = (self.config.get('vr'))
        if isinstance(vr_id, str) and vr_id.isdigit():
            vr_id = int(vr_id)
        self.vr = device_pool['vr'].get(vr_id)
        if self.vr:
            self.vr.on("message",self.teleop.handle_socket_data)
        # 摄像头（可选）
        # 可按需扩展摄像头相关逻辑
        self.running = True

    def stop(self):
        # 仅停止teleop逻辑，不操作设备
        if self.vr:
            self.vr.off("message")
        if self.left_arm:
            self.teleop.off("leftGripDown")
            self.teleop.off("leftGripUp")
        if self.right_arm:
            self.teleop.off("rightGripDown")
            self.teleop.off("rightGripUp")
        self.running = False
