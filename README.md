# 如何使用
- Teleoperation.py中设置RM_controller的ip为对应的左右臂ip,Host设置为Quest的ip
- 运行Teleoperation().run()启动遥操作相关的线程(注意需要在主线程While True阻止主线程退出)

# 代码介绍
## RealMan.py
RealMan.py里封装了RM_controller类,在初始化时会启动获取realman机械臂位姿的轮询线程,RM_controller.get_state()直接返回自变量值而不是使用睿尔曼的接口

## Teleoperation
该类封装了两个线程分别是
- receiver_thread:从Quest获取手柄数据并在处理后同步给睿尔曼机械臂
- sender_thread:反馈线程,将末端位姿传回Quest,暂时没啥用