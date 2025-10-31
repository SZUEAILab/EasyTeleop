from EasyTeleop.TeleopGroup import SingleArmWithTriggerTeleopGroup

from EasyTeleop.Device.VR import VRSocket
from EasyTeleop.Device.Robot import RealMan

from EasyTeleop.Device import get_device_types, get_device_classes
from EasyTeleop.TeleopGroup import get_teleop_group_types, get_teleop_group_classes

print(get_device_types())
print(get_device_classes())
print(get_teleop_group_types())
print(get_teleop_group_classes())

vr = VRSocket({'ip': '192.168.0.120', 'port': 12345})
arm = RealMan({'ip': '192.168.0.18', 'port': 8080})

teleopgroup = SingleArmWithTriggerTeleopGroup([arm,vr,None,None ])
teleopgroup.start()

while True:
    states = vr.get_conn_status()
    print(f"设备连接状态: {states}")
    import time
    time.sleep(1)