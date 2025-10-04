# 话题设计
考虑到MQTT有通配符#的概念能简化订阅过程，所以采用以下的话题设计
### node/{id}/status
节点状态话题，数据盒子Node后向该话题发送payload=1的消息
注意Node上线后需要注册好LWT（遗嘱消息），内容是向该话题发送payload=0的消息
### node/{id}/device/{id}/status
由Node发布，payload为0,1,2分别代表
- 0-设备未启动
- 1-设备启动且连接成功
- 2-设备启动但链接出现问题正在尝试重连
### node/{id}/teleop-group/{id}/status 
遥操组启动状态
0-未启动
1-已启动
### node/{id}/teleop-group/{id}/collecting
遥操组的采集状态
- 0-未采集
- 1-采集中