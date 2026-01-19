# Language

- [中文](#中文)
- [English](#english)

---

## 中文
---
### SDK包目录
   
|-- include               //头文件目录  
|-- sdk_lib               //动态库目录  
|---- ffmpeg3             //ffmpeg库  
|---- nvidia              //nvidia平台动态库  
|---- soft                //通用平台动态库，支持rk加速  
|---- device.pem          //公有云证书   
|---- GetDeviceInfo       //设备指纹查看工具  
|---- run_loader.sh       //demo运行脚本，会自动设置依赖库路径并启动程序  
|---- trro_sample.cpp     //demo源码  
|---- trro-test           //demo程序  
|---- config_gen.py       //配置生成脚本，可生成config.json配置文件；建议优先使用web工具生成

---
### 编译说明
编译命令可参考  
g++ trro_sample.cpp -o trro-test  -I ./include -L ./sdk_lib/ -L ./sdk_lib/soft -ltrro_field -lrtc_media -lrtc_engine -pthread -ldl -Wl,--rpath-link=./sdk_lib/ffmpeg3  
注意：
- 如果跨平台编译，需要使用跨平台对应的g++；
- 如果编译提示有缺少依赖库，可尝试加入-Wl，--unresolved-symbols=ignore-in-shared-libs

---
### 配置生成

#### web工具生成（推荐）
- 公有云
    1. 访问页面 https://console.cloud.tencent.com/trro/config 生成现场设备配置
    2. 复制生成的配置JSON内容，替换到本地config.json文件

- 私有化
    1. 最小配置启动demo。修改config.json, 填写device_id和server_ip，私有化下最小配置为  
    {  
      "device_id":"test_gw",  
      "device_name":"test_gw",  
      "server_ip":"xxx.xxx.xxx.xxx",  
      "server_port":2883  
    }  
    2. 设备启动后，给设备在线下发视频传输配置。登陆后台运维管理web的配置页面 ( http://serverip:8190/config_template )，通过web创建配置模板，并下发给设备。

#### python脚本生成（建议优先web工具）
1. 修改config_gen.py中的配置；
2. 运行python config_gen.py 自动生成并替换config.json

---
### 运行说明
1. 按配置生成建议，修改config.json配置文件
2. 确认./run_loader.sh中正确引用对应平台（nvidia/soft）的动态库路径
3. 执行./run_loader.sh， 如果提示权限不足，可先chmod +X ./run_loader.sh

注意：
- 多网卡绑定时需要用root权限执行，或者在执行前添加权限  
      sudo setcap cap_net_raw,cap_net_bind_service+ep ./trro-test

---
### 官网文档
https://cloud.tencent.com/document/product/1584  
可参看现场SDK说明部分



---
## English
---
### SDK Package Tree
|— include  
|— sdk_lib  
|— — ffmpeg3    //ffmpeg libs  
|— — nvidia     //nvidia jetson platform libs  
|— — soft       //common aarch64 platform libs  
|— device.pem       //cloud cerfiticate  
|— run_loader.sh    //demo run script  
|— trro_sample.cpp  //demo source code  
|— trro-test        //demo program  
|— config_gen.py    //configuration generation python script  

---
### Compile Description  
compile g++ command  
g++ trro_sample.cpp -o trro-test  -I ./include -L ./sdk_lib/ -L ./sdk_lib/soft -ltrro_field -lrtc_media -lrtc_engine -pthread -ldl -Wl,--rpath-link=./sdk_lib/ffmpeg3  
note： 
- for cross-platform compile, using aarch64-linux-gnu-g++
- to avoid the missed libs,  add the option  -Wl.--unresolved-symbols=ignore-in-shared-libs

---
### Configuration
- revise config.json directly with or without the tools https://console.tencentcloud.com/trro/config
- using python script to generate
  1. revise the config_gen.py
  2. run python config_gen.py to generate config.json
Note:
- for the international site, "cloud_mode" should be configured as "public_intl"

---
### Run Demo
1. revise config.json, refer to [Configuration](#Configuration)
2. revise ./run_loader.sh，using the correct LD_LIBRARY_PATH for libs
    - ./sdk_lib/nvidia for nvidia jetson platform
    - ./sdk_lib/soft for common aarch64 platform  
3. run ./run_loader.sh，if not permitted，try chmod +X ./run_loader.sh  

Note: 
- if using multiple networks transmission,  recommend to run the program under root permission or  add the permission to trro_test  
sudo setcap cap_net_raw,cap_net_bind_service+ep ./trro-test

### SDK Document
https://www.tencentcloud.com/document/product/1252/67790