# 如何使用
- 运行run.py直接启动
- 注意每个类都要start一下来启动相关线程

# 代码介绍
## RealMan.py
RealMan.py里封装了RM_controller类,在初始化时会启动获取realman机械臂位姿的轮询线程,RM_controller.get_state()直接返回自变量值而不是使用睿尔曼的接口

## Teleoperation
该类封装了两个线程分别是
- receiver_thread:从Quest获取手柄数据并在处理后同步给睿尔曼机械臂
- sender_thread:反馈线程,将末端位姿传回Quest,暂时没啥用