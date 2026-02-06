from .BaseTeleopGroup import BaseTeleopGroup
import threading
import time
import logging

# 创建日志记录器
logger = logging.getLogger(__name__)

class TwoArmWithTriggerTeleopGroup(BaseTeleopGroup):
    """支持双臂+VR+3摄像头的标准配置,启用夹爪控制,A键切换采集状态,摄像头可以留空"""
    
    # 遥操组类型名称
    name = "双臂+夹爪+3摄像头遥操组"
    
    # 遥操组类型描述
    description = "支持双臂+VR+3摄像头的标准配置,启用夹爪控制,A键切换采集状态,摄像头可以留空"
    
    # 遥操组所需配置字段
    need_config = [
        {
            "name": "left_arm",
            "description": "左臂设备",
            "category": "Robot"
        },
        {
            "name": "right_arm", 
            "description": "右臂设备",
            "category": "Robot"
        },
        {
            "name": "vr",
            "description": "VR设备",
            "category": "VR"
        },
        {
            "name": "camera1",
            "description": "摄像头1",
            "category": "Camera"
        },
        {
            "name": "camera2",
            "description": "摄像头2",
            "category": "Camera"
        },
        {
            "name": "camera3",
            "description": "摄像头3",
            "category": "Camera"
        }
    ]

    def __init__(self, devices = None):
        super().__init__(devices)

    def start(self) -> bool:
        """
        启动默认遥操组
        :return: 是否启动成功
        """
        try:
            print("启动默认遥操组")
            
            # 启动数据采集
            self.data_collect.start()
            self.teleop.on("buttonATurnDown", self.data_collect.toggle_capture_state)
            # 注册数据采集状态变化回调
            # self.data_collect.on("status_change",None)
            
            left_robot = self.devices[0]
            right_robot = self.devices[1]
            vr_device = self.devices[2]

            # 注册回调函数

            if vr_device:
                vr_device.on("message",self.teleop.handle_socket_data)
                self.robot_feedback_packer.on("packet", vr_device.add_feedback_data)

            if left_robot:
                self.teleop.on("leftGripTurnDown", left_robot.start_control)
                self.teleop.on("leftGripTurnUp", left_robot.stop_control)
                self.teleop.on("leftTrigger", left_robot.add_end_effector_data)
                self.teleop.on("leftPosRot", left_robot.add_pose_data)

                @left_robot.on("pose")
                def handle_left_pose(pose, arm_id=0):
                    self.data_collect.put_robot_pose(pose, arm_id=arm_id)
                    self.robot_feedback_packer.add_feedback(left_robot, arm_id=arm_id, pose=pose)

                @left_robot.on("joint")
                def handle_left_joint(joint, arm_id=0):
                    self.data_collect.put_robot_joint(joint, arm_id=arm_id)
                    self.robot_feedback_packer.add_feedback(left_robot, arm_id=arm_id, joints=joint)

                @left_robot.on("end_effector")
                def handle_left_end_effector(eff, arm_id=0):
                    self.data_collect.put_end_effector_state(eff, arm_id=arm_id)
                    self.robot_feedback_packer.add_feedback(left_robot, arm_id=arm_id, end_effector=eff)
                    
            if right_robot:
                self.teleop.on("rightGripTurnDown", right_robot.start_control)
                self.teleop.on("rightGripTurnUp", right_robot.stop_control)
                self.teleop.on("rightTrigger", right_robot.add_end_effector_data)
                self.teleop.on("rightPosRot", right_robot.add_pose_data)

                @right_robot.on("pose")
                def handle_right_pose(pose, arm_id=1):
                    self.data_collect.put_robot_pose(pose, arm_id=arm_id)
                    self.robot_feedback_packer.add_feedback(right_robot, arm_id=arm_id, pose=pose)

                @right_robot.on("joint")
                def handle_right_joint(joint, arm_id=1):
                    self.data_collect.put_robot_joint(joint, arm_id=arm_id)
                    self.robot_feedback_packer.add_feedback(right_robot, arm_id=arm_id, joints=joint)

                @right_robot.on("end_effector")
                def handle_right_end_effector(eff, arm_id=1):
                    self.data_collect.put_end_effector_state(eff, arm_id=arm_id)
                    self.robot_feedback_packer.add_feedback(right_robot, arm_id=arm_id, end_effector=eff)

            

            if self.devices[3]:
                self.devices[3].on("frame",lambda frame, camera_id=0: self.data_collect.put_video_frame(frame, camera_id=camera_id))
            if self.devices[4]:
                self.devices[4].on("frame",lambda frame, camera_id=1: self.data_collect.put_video_frame(frame, camera_id=camera_id))
            if self.devices[5]:
                self.devices[5].on("frame",lambda frame, camera_id=2: self.data_collect.put_video_frame(frame, camera_id=camera_id))
            
            # 启动所有设备
            for device in self.devices:
                if device:
                    device.start()
                
            self.running = True
            
            # 触发状态变化事件
            self.emit("status_change", 1)
            return True
        except Exception as e:
            print(f"启动默认遥操组失败: {e}")
            return False

    def stop(self) -> bool:
        """
        停止默认遥操组
        :return: 是否停止成功
        """
        try:
            print("停止默认遥操组")
            
            # 触发状态变化事件（停止前）
            self.running = False
            
            # 停止所有设备
            for device in self.devices:
                if device:
                    device.stop()
            
            # 停止数据采集
            self.data_collect.stop()
            
            # 需要等待数采后处理完毕
            
            self.emit("status_change", 0)
            
            self.devices.clear()
            return True
        except Exception as e:
            print(f"停止默认遥操组失败: {e}")
            return False
