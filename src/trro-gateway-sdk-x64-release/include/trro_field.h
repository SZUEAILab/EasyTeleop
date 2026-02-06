/*! @file trro_field.h */
#ifndef TRRO_FIELD_H
#define TRRO_FIELD_H
#define TRRO_EXPORT __attribute__((visibility("default")))
#define DEPRECATED __attribute__((deprecated))

/* 通用错误码 */
/**
 * @deprecated 已被废弃，不再推荐使用。请使用 TRRO_SUCCEED代替。
 * @def TRRO_SUCCED
 * @brief 十进制【1】
 * 成功
 */
#define TRRO_SUCCED           		                        0x00000001 

/* 通用错误码 */
/**
 * @def TRRO_SUCCEED
 * @brief 十进制【1】
 * 成功
 */
 #define TRRO_SUCCEED           		                        0x00000001 

/**
 * @def TRRO_COMMON_ERROR
 * @brief 十进制【16777215】
 * 失败
 */
#define TRRO_COMMON_ERROR                                   0x00FFFFFF 

/* 配置文件加载模块*/
/**
 * @def TRRO_CONFIG_ERROR
 * @brief 十进制【33554431】
 * 配置解析失败
 */
#define TRRO_CONFIG_ERROR                                   0x01FFFFFF 

/**
 * @def TRRO_CONFIG_PARSE_FAILED
 * @brief 十进制【16777218】
 *  配置文件格式异常
 */
#define TRRO_CONFIG_PARSE_FAILED                            0x01000002 

/**
 * @def TRRO_CONFIG_ILLEGAL
 * @brief 十进制【16777219】 
 * 参数格式非法，需新增参数检查
 */
#define TRRO_CONFIG_ILLEGAL                                 0x01000003 

/**
 * @def TRRO_CONFIG_UNEXIST
 * @brief 十进制【16777220】 
 * 配置文件不存在
 */
#define TRRO_CONFIG_UNEXIST                                 0x01000004 

/**
 * @def TRRO_CONFIG_CER_FAILED
 * @brief 十进制【16777221】 
 * 云证书错误
 */
#define TRRO_CONFIG_CER_FAILED                              0x01000005

/**
 * @def TRRO_CONFIG_LIC_FAILED
 * @brief 十进制【16777222】
 * license证书错误
 */
#define TRRO_CONFIG_LIC_FAILED                              0x01000006

/**
 * @def TRRO_CONFIG_STREAMS_SIZE_ERROR
 * @brief 十进制【16777223】
 * 超过最大支持流数目
 */
#define TRRO_CONFIG_STREAMS_SIZE_ERROR                      0x01000007

/**
 * @def TRRO_CONIFG_PORT_RANGE_ILLEGAL
 * @brief 十进制【16777224】
 * 端口范围配置非法
 */
#define TRRO_CONIFG_PORT_RANGE_ILLEGAL                      0x01000008

/**
 * @def TRRO_CONFIG_LOG_PERMISSON_DENIED
 * @brief 十进制【16777225】
 * 打开log文件权限不足
 */
#define TRRO_CONFIG_LOG_PERMISSON_DENIED                    0x01000009 

/* 初始化模块 */
/**
 * @def TRRO_INIT_ERROR
 * @brief 十进制【50331647】 
 * 初始化通用失败
 */
#define TRRO_INIT_ERROR                                     0x02FFFFFF

/**
 * @def TRRO_INIT_INPUT_ILLEGAL
 * @brief 十进制【33554434】 
 * 初始化参数异常
 */
#define TRRO_INIT_INPUT_ILLEGAL                             0x02000002

/**
 * @def TRRO_INIT_PARSE_FAILED
 * @brief 十进制【33554435】 
 * 配置节点解析异常
 */
#define TRRO_INIT_PARSE_FAILED                              0x02000003

/**
 * @def TRRO_INIT_CREAT_MEDIAMODE_FAILED
 * @brief 十进制【33554436】
 * 媒体模块创建失败
 */
#define TRRO_INIT_CREAT_MEDIAMODE_FAILED                    0x02000004

/**
 * @def TRRO_INIT_PRM_ERROR
 * @brief 十进制【33554437】
 * 参数错误
 */
#define TRRO_INIT_PRM_ERROR                                 0x02000005

/**
 * @def TRRO_INIT_INVALUDE_INPUT
 * @brief 十进制【33554438】
 * 非法输入
 */
#define TRRO_INIT_INVALUDE_INPUT                            0x02000006

/**
 * @def TRRO_INIT_REPEAT
 * @brief 十进制【33554439】
 * 重复初始化
 */
#define TRRO_INIT_REPEAT                                    0x02000007


/**
 * @def TRRO_INIT_LICENSE_CHECK_FAILED
 * @brief 十进制【33554448】
 * LICENSE校验失败
 */
#define TRRO_INIT_LICENSE_CHECK_FAILED                      0x02000010

/**
 * @def TRRO_INIT_LICENSE_FILE_ERROR
 * @brief 十进制【33554449】
 * LICENSE 文件错误
 */
#define TRRO_INIT_LICENSE_FILE_ERROR                        0x02000011

/**
 * @def TRRO_INIT_LICENSE_CHECK_TIME_FAILED
 * @brief 十进制【33554450】
 * LICENSE 授权过期
 */
#define TRRO_INIT_LICENSE_CHECK_TIME_FAILED                 0x02000012

/**
 * @def TRRO_INIT_LICENSE_CHECK_DEVICE_FAILED
 * @brief 十进制【33554451】
 * LICENSE 硬件验证失败
 */
#define TRRO_INIT_LICENSE_CHECK_DEVICE_FAILED               0x02000013

/**
 * @def TRRO_INIT_LICENSE_CHECK_STREM_FAILED
 * @brief 十进制【33554452】
 * LICENSE 授权流小于设备流
 */
#define TRRO_INIT_LICENSE_CHECK_STREM_FAILED                0x02000014

/**
 * @def TRRO_INIT_LICENSE_CHECK_ID_FAILED
 * @brief 十进制【33554453】
 * LICENSE 设备ID验证失败
 */
#define TRRO_INIT_LICENSE_CHECK_ID_FAILED                   0x02000015


/**
 * @def TRRO_INIT_PUBLIC_LICENSE_CHECK_TIMEOUT
 * @brief 十进制【33554688】
 * LICENSE 公有云license验证超时
 */
#define TRRO_INIT_PUBLIC_LICENSE_CHECK_TIMEOUT              0x02000100

/**
 * @def TRRO_INIT_PUBLIC_LICENSE_CHECK_NOT_BIND
 * @brief 十进制【33554689】
 * LICENSE 公有云设备未绑定license
 */
#define TRRO_INIT_PUBLIC_LICENSE_CHECK_NOT_BIND             0x02000101

/**
 * @def TRRO_INIT_PUBLIC_LICENSE_CHECK_NOT_ENOUGH
 * @brief 十进制【33554690】
 * LICENSE 公有云license数量不足
 */
#define TRRO_INIT_PUBLIC_LICENSE_CHECK_NOT_ENOUGH           0x02000102

/**
 * @def TRRO_INIT_PUBLIC_LICENSE_CHECK_OVERTIME
 * @brief 十进制【33554691】
 * LICENSE 公有云license已过期
 */
#define TRRO_INIT_PUBLIC_LICENSE_CHECK_OVERTIME             0x02000103

/**
 * @def TRRO_INIT_PUBLIC_LICENSE_CHECK_NOT_DURATION
 * @brief 十进制【33554692】
 * LICENSE 公有云license剩余时长不足
 */
#define TRRO_INIT_PUBLIC_LICENSE_CHECK_NOT_DURATION          0x02000104

/* 信令服务器模块 */

/**
 * @def TRRO_SIGNAL_ERROR
 * @brief 十进制【67108863】
 * 信令模块失败
 */
#define TRRO_SIGNAL_ERROR                                   0x03FFFFFF

/**
 * @def TRRO_SIGNAL_REGIST_FAILED
 * @brief 十进制【50331650】
 * 信令注册失败
 */
#define TRRO_SIGNAL_REGIST_FAILED                           0x03000002

/**
 * @def TRRO_SIGNAL_STATUS_ABNORMAL
 * @brief 十进制【50331651】
 * 信令服务器连接异常
 */
#define TRRO_SIGNAL_STATUS_ABNORMAL                         0x03000003

/**
 * @def TRRO_SIGNAL_MESSAGE_FAILED
 * @brief 十进制【50331652】
 * 信令消息处理失败
 */
#define TRRO_SIGNAL_MESSAGE_FAILED                          0x03000004 

/**
 * @def TRRO_SIGNAL_CONNECT_OUTTIME
 * @brief 十进制【50331653】
 * 信令服务器连接超时
 */
#define TRRO_SIGNAL_CONNECT_OUTTIME                         0x03000005

/**
 * @def TRRO_SIGNAL_DEVICEID_OR_PASSWORD_INCORRECT
 * @brief 50331654
 * 信令服务器连接用户名或者密码错误
 */
#define TRRO_SIGNAL_DEVICEID_OR_PASSWORD_INCORRECT          0x03000006

/**
 * @def TRRO_DEVICE_ALREADY_LOGIN
 * @brief 50331655
 * 信令服务器连接用户名已经登陆
 */
#define TRRO_DEVICE_ALREADY_LOGIN                           0x03000007

/* 流采集模块 */

/**
 * @def TRRO_CAPTURE_ERROR
 * @brief 十进制【83886079】
 * 采集模块错误
 */
#define TRRO_CAPTURE_ERROR                                  0x04FFFFFF

/**
 * @def TRRO_CAPTURE_OPENDEVICE_FAILED
 * @brief 十进制【67108866】
 * 打开设备失败
 */
#define TRRO_CAPTURE_OPENDEVICE_FAILED                      0x04000002

/**
 * @def TRRO_CAPTURE_GETSOURCE_FAILED
 * @brief 十进制【67108867】
 * 获取数据源失败
 */
#define TRRO_CAPTURE_GETSOURCE_FAILED                       0x04000003

/**
 * @def TRRO_CAPTURE_UNKNOWN_CAPTURETYPE
 * @brief 十进制【67108868】
 * 未知采集类型
 */
#define TRRO_CAPTURE_UNKNOWN_CAPTURETYPE                    0x04000004

/* 流传输模块 */

/**
 * @def TRRO_CONNECT_ERROR
 * @brief 十进制【100663295】
 * 连接错误
 */
#define TRRO_CONNECT_ERROR                                  0x05FFFFFF

/**
 * @def TRRO_CONNECT_OUTTIME
 * @brief 十进制【83886082】
 * 超时断连
 */
#define TRRO_CONNECT_OUTTIME                                0x05000002

/**
 * @def TRRO_MESSAGE_ERROR
 * @brief 十进制【117440511】
 * 消息错误
 */
#define TRRO_MESSAGE_ERROR                                  0x06FFFFFF 

/**
 * @def TRRO_MESSAGE_CHANNEL
 * @brief 十进制【100663298】
 * 消息通道异常
 */
#define TRRO_MESSAGE_CHANNEL                                0x06000002

/**
 * @def TRRO_MESSAGE_BYTE_EXCEED
 * @brief 十进制【100663299】
 * 发送字节数超出限制
 */
#define TRRO_MESSAGE_BYTE_EXCEED                            0x06000003

/**
 * @def TRRO_MESSAGE_RATE_EXCEED
 * @brief 十进制【100663300】
 * 发送间隔过于密集
 */
#define TRRO_MESSAGE_RATE_EXCEED                            0x06000004

/**
 * @def TRRO_MESSAGE_MAX_EXCEED
 * @brief 十进制【100663301】
 * 1s钟最多发送 10KB数据
 */
#define TRRO_MESSAGE_MAX_EXCEED                             0x06000005

/**
 * @def TRRO_BYTE_EXCEED_ERROR
 * @brief 十进制【100663302】
 * 发送缓冲区满了
 */
#define TRRO_MESSAGE_BLOCK                                  0x06000006

/**
 * @def TRRO_MESSAGE_PERMISSION
 * @brief 十进制【100663303】
 * 消息压缩失败
 */
#define TRRO_MESSAGE_COMPRESS                               0x06000007

/**
 * @def TRRO_MESSAGE_PERMISSION
 * @brief 十进制【100663304】
 * 没有接受端存在，接受权限问题
 */
#define TRRO_MESSAGE_PERMISSION                             0x06000008


/**
 * @def TRRO_STOR_ERROR
 * @brief 十进制【134217727】
 * 存储异常
 */
#define TRRO_STOR_ERROR                                     0x07FFFFFF

/**
 * @def TRRO_STOR_UNENABLE
 * @brief 十进制【117440513】
 * 存储未使能
 */
#define TRRO_STOR_UNENABLE                                  0x07000001

/**
 * @def TRRO_STOR_IDEXIST
 * @brief 十进制【117440514】
 * 重复开启存储
 */
#define TRRO_STOR_IDEXIST                                   0x07000002

/**
 * @def TRRO_STOR_ID_ILLEGAL
 * @brief 十进制【117440515】
 * 非法ID
 */
#define TRRO_STOR_ID_ILLEGAL                                0x07000003

/**
 * @def TRRO_STOR_PARAM_ILLEGAL
 * @brief 十进制【117440516】
 * 参数非法
 */
#define TRRO_STOR_PARAM_ILLEGAL                             0x07000004

/**
 * @def TRRO_STOR_UNSET_FILENAME
 * @brief 十进制【117440517】
 * 未设置文件名
 */
#define TRRO_STOR_UNSET_FILENAME                            0x07000005

/**
 * @def TRRO_START_CAPTURE_IDEXIST
 * @brief 十进制【117440518】
 * 重复开启采集
 */
#define TRRO_START_CAPTURE_IDEXIST                          0x07000006

/**
 * @def TRRO_EXTERNAL_RESIZE
 * @brief 十进制【134217729】
 * 外采模式错误
 */
#define TRRO_EXTERNAL_RESIZE                                0x08000001

/* 异步回调错误码 */
/**
 * @def TRRO_ERROR_CALLBACK_CAMERA
 * @brief 十进制【151060480】
 * 相机异步回调错误
 */
#define TRRO_ERROR_CALLBACK_CAMERA                          0x09010000  

/**
 * @def TRRO_ERROR_CALLBACK_MIC
 * @brief 十进制【151126016】
 * 麦克风异步回调错误
 */
#define TRRO_ERROR_CALLBACK_MIC                             0x09020000      

/**
 * @def TRRO_ERROR_CALLBACK_BANDWIDTH_LIMIT
 * @brief 十进制【151191552】
 * 评估网络带宽无法满足最低码率需求
 */
#define TRRO_ERROR_CALLBACK_BANDWIDTH_LIMIT                 0x09030000      
                   
/**
 * @def TRRO_ERROR_CALLBACK_RESERVE_DEGRADE
 * @brief 十进制【151257088】
 * 网络带宽不足引发reserve带宽降级
 */
#define TRRO_ERROR_CALLBACK_RESERVE_DEGRADE                 0x09040000      

/**
 * @def TRRO_UNSUPPORT
 * @brief 十进制【251658241】
 * 该调用或者函数功能暂不支持
 */
#define TRRO_UNSUPPORT                                      0x0F000001

/**
 * TrroState trro连接状态枚举
 */
enum TrroState {
    kDisconnect = 0, /**< 断连 */
    kConnecting = 1, /**< 连接中 */
    kConnected = 2,  /**< 已连接 */
    kDisconnecting = 3, /**< 已断连 */
};

/**
 * TrroPermission 权限枚举
 */
enum TrroPermission {
    kPermissionGuest = 0, /**< guest权限 */
    kPermissionMaster = 1,  /**< master权限 */
};

/**
 * TrroColor 颜色枚举
 */
enum TrroColor{
     Trro_ColorYUVI420 = 0, /**< YUVI420 */
     Trro_ColorUYVY    = 3, /**< UYVY   */
     Trro_ColorYUYV    = 4, /**< YUYV  */
     Trro_ColorJPEG    = 5, /**< JPEG  */
     Trro_ColorARGB    = 6, /**< ARGB  */
     Trro_ColorNV12    = 7, /**< NV12  */
     Trro_ColorMJPEG   = 8, /**< MJPEG */
     Trro_ColorEYUYV   = 9, /**< eyuyv */

     /* encode type */
     Trro_ColorH264    = 10,
     Trro_ColorH265    = 11,
     Trro_ColorAV1     = 12,
};

/**
 * FrameType 帧类型枚举
 */
enum FrameType{
    TYPE_IFrame = 1, /**< I帧 */
    TYPE_PFrame = 0, /**< P帧 */
};

/**
 * SignalState 信令连接状态枚举
 */
enum SignalState {
    kTrroReady = 0, /**< 连接建立成功 */
    kTrroLost = 1,  /**< 连接断开，内部会进行自动重连 */
    kTrroReup = 2,  /**< 自动重连成功 */
    kTrroKickout = 3,
    kTrroAuthFailed = 4,  /**< 用户名或者密码错误 */
};

/**
 * TrroLogLevel 日志等级枚举
 */
enum TrroLogLevel {
	TRRO_LOG_INFO = 1, /**< INFO */
	TRRO_LOG_WARNING = 2, /**< WARNING */
	TRRO_LOG_ERROR = 3, /**< ERROR */
};

/**
 * MediaDeviceType 设备类型枚举
 */
enum MediaDeviceType {
    ///麦克风类型设备
    MediaDeviceTypeMic = 0,
    ///扬声器类型设备
    MediaDeviceTypeSpeaker = 1,
};

/**
 * VideoCaptureProtocol 采集类型
 */
enum VideoCaptureProtocol {
 kV4L2_DMA = 0, /**< DMA硬件加速 */
 kV4L2_MMAP, /**< 内存映射 */
 kRTSP, /**< RTSP类型 */
};

struct TrroMultiNetworkStats {

    char local_ip[16];
    int local_port;
    char extern_ip[16];
    int extern_port;

    float rtt;
    float lost;
    unsigned long long send_bytes;
    unsigned long long recv_bytes;
};

/**
* @name TRRO_OnMultiNetworkStat
* @brief  回调所绑定的每个网卡的内网IP，外网IP， rtt、lost 接收数据和发送数据
* @param[in]     stats
* @return void
*/
typedef void TRRO_onMultiNetworkStat(void* context, const TrroMultiNetworkStats stats);

/**
* @name TRRO_onState
* @brief 视频连接状态回调
* @param[in]     context        上下文
* @param[in]     stream_id      视频流id
* @param[in]     state          TrroState连接状态
* @return void
*/
typedef void TRRO_OnState(void* context, int stream_id, int state);

/**
* @name TRRO_OnErrorEvent
* @brief 错误信息回调
* @param[in] context        上下文
* @param[in] error_code     错误码  为负值
* @param[in] error_msg      错误信息
* @return void
*/
typedef void TRRO_OnErrorEvent(void* context, int error_code, const char* error_msg);

/**
* @name TRRO_onControlData
* @brief 接收远端设备消息回调
* @param[in]     context        上下文指针，返回注册时传入的context
* @param[in]     controller_id  远端设备ID
* @param[in]     msg            消息体内容
* @param[in]     qos            消息体长度
* @param[in]     msg            消息qos类型 0:unreliable, 1:reliable
* @return void
*/
typedef void TRRO_onControlData(void *context, const char *controller_id, const char* msg, int len, int qos);

/**
* @name TRRO_onVideoCaptureData
* @brief 采集视频帧回调
* @param[in]     context        上下文指针，返回注册时传入的context
* @param[in]     data           视频数据
* @param[in]     width          宽
* @param[in]     height         高
* @param[in]     type           视频格式,0 YUV420, 4 YUYV
* @param[in]     stream_id      流号
* @return void 
*/
typedef void TRRO_onVideoCaptureData(void *context, const char* data, int width, int height, int type, int stream_id);

/**
* @name TRRO_OnLogData
* @brief 日志回调
* @param[in]     context        上下文
* @param[in]     msg            日志内容
* @param[in]     level          日志级别,参考枚举TrroLogLevel
* @return void 
*/
typedef void TRRO_OnLogData(void *context, const char *msg, int level);

/**
* @name TRRO_onEncodeFrameInfo
* @brief 编码建议信息回调，适用于外部输入编码帧场景
* @param[in]     context        上下文
* @param[in]     stream_id      流ID
* @param[in]     type           回调类型， 0：强制关键帧请求 ,  1 码率更新请求 
* @param[in]     bitrate        type为1时有效，表示建议输入的编码数据码率，单位kbps 
* @return void 
*/
typedef void TRRO_onEncodeFrameInfo(void *context, int stream_id, int type, int bitrate);

/**
* @name TRRO_onLatencyReport
* @brief 延迟信息回调
* @param[in]     context        上下文
* @param[in]     stream_id      流ID
* @param[in]     vcct           视频控制闭环时延， 等于视频上行延迟（不含采集）+控制下行延迟
* @return void 
*/
typedef void TRRO_onLatencyReport(void *context, int stream_id, int vcct);

/**
* @name TRRO_onMediaState
* @brief 媒体传输状态回调
* @param[in]   context      回调上下文指针
* @param[in]   stream_id    流ID 
* @param[in]   fps          每秒帧数目
* @param[in]   bps          每秒数据量
* @param[in]   rtt          封包来回时间
* @param[in]   lost         丢包率
* @param[in]   packets_send 总发送数目
* @param[in]   stun         穿网模式 0：host, 1：srflx, 2：prflx, 3：relay
* @return void 
*/
typedef void TRRO_onMediaState(void* context, int stream_id, int fps, int bps, int rtt, long long lost, long long packets_send, int stun);


/**
* @name TRRO_onSignalState
* @brief 信令连接状态回调
* @param[in]     context        上下文
* @param[in]     state          信令连接状态，参考枚举SignalState
* @return void 
*/
typedef void TRRO_onSignalState(void *context, SignalState state);

/**
* @name TRRO_onOperationPermissionRequest
* @brief 远端设备操控权限申请通知
* @param[in]     remote_devid        请求权限的remote deviceId
* @param[in]     permission          请求的权限，参考TrroPermission，  0: guest 只有观看权限,  1: master 完全控制权限
* @return void 
*/
typedef void TRRO_onOperationPermissionRequest(void* context, const char* remote_devid, int permission);

/**
 * @name TRRO_onVideoCaptureFrame
 * @brief 外部调用TRRO_startVideoCapture时的数据回调
 * @param[in] context      上下文
 * @param[in] capture_id   采集视频的当前源ID
 * @param[in] data         采集的视频数据
 * @param[in] length       采集的视频数据长度
 * @param[in] width        采集的视频宽度
 * @param[in] height       采集的视频高度
 * @param[in] color_format 采集的视频格式
 * @return void
 */
typedef void TRRO_onVideoCaptureFrame(void *context, unsigned long long capture_id, const char* data, int length, int width, int height, TrroColor color_format);

/** 
* @name  TRRO_onRemoteMixAudioFrame
* @brief 对端多路混音后音频原始数据回调
* @param[in] context     回调上下文指针, 返回注册回调函数时传入的context
* @param[in] data        音频PCM数据 10ms 16bits
* @param[in] length      数据长度
* @param[in] channel     音频声道数目，如单声道为1，双声道为2，多声道为N
* @param[in] sample_rate   音频采样率
* @return : void
*/

typedef void TRRO_onRemoteMixAudioFrame(void* context, const char* data, int length, int channel, int sample_rate);

/**
* @name  getErrorMsg
* @brief 根据错误码，返回错误信息。
* @param[in] errorCode   错误码
* @return errorMsg   排查帮助信息
*/
extern "C" TRRO_EXPORT const char* getErrorMsg(int errorCode);

/**
* @name  TRRO_initGwJsonWithLicense
* @brief 使用字符串和本地license初始化
* @param[in] json_str        配置文件json字符串
* @param[in] license_path    license文件路径名，e.g. "./license.txt"
* @param[in] mode            初始化模式 0 同步模式一直等待，-1 异步模式, 初始化成功后通知TRRO_onSignalState
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_initGwJsonWithLicense(const char * json_str, const char * license_path, int mode = 0);

/**
* @name  TRRO_initGwJson
* @brief 使用字符串初始化
* @param[in] json_str        配置文件json字符串
* @param[in] mode             0 同步模式，一直等待 -1 异步模式，初始化成功后通知TRRO_onSignalState
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_initGwJson(const char * json_str, int mode = 0);

/**
* @name TRRO_initGwPathWithLicense
* @brief 使用配置文件和本地license初始化
* @param[in] cfg_path        json配置文件路径名，e.g. "./config.json"
* @param[in] license_path    license文件路径名，e.g. "./license.txt"
* @param[in] mode             0 同步模式一直等待，-1 异步模式 初始化成功后通知TRRO_onSignalState
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_initGwPathWithLicense(const char * cfg_path, const char * license_path, int mode = 0);

/**
* @name TRRO_initGwPath
* @brief 使用配置文件初始化
* @param[in] cfg_path        json配置文件路径名，e.g. "./config.json"
* @param[in] mode            0  同步模式一直等待，-1 异步模式，初始化成功后TRRO_onSignalState信息
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_initGwPath(const char * cfg_path, int mode = 0);

/**
* @name TRRO_start
* @brief 启动音视频传输业务， 需要等待初始化成功后调用（同步模式init返回成功 或 异步模式初始化TRRO_onSignalState通知连接Read）
* @param[in] void
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_start();

/**
* @name TRRO_stop
* @brief 销毁SDK，释放sdk资源
* @param[in]  void
* @return void
*/
extern "C" TRRO_EXPORT void TRRO_stop();

/**
* @name   TRRO_sendControlData
* @brief  向远端设备发送数据
* @param[in] msg            消息体
* @param[in] len            消息体长度
* @param[in] qos            0:unreliable 1:reliable
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_sendControlData(const char* msg, int len, int qos = 0);


/**
 * @name TRRO_setChineseFontAndSize(Experimental)
 * @brief 设置渲染文字格式，需要在调用外部输入图像前前调用，否则不生效
 * @param[in] font_path                        字幕格式路径 .tff 后缀的路径
 * @param[in] size                             字幕大小
 * @param[in] input                            需要输入的文字字符集合
 * @return void
*/
extern "C" TRRO_EXPORT void TRRO_setChineseFontAndSize(const char* font_path, float size, const char* input);

/**
* @name   TRRO_externalVideoData
* @brief  废弃的外部图像输入接口
* @deprecated 这个接口已被废弃，不再推荐使用。请使用 TRRO_externalVideoDataWithText 接口代替。
* @param[in]   stream_id     流ID
* @param[in]   data          消息体
* @param[in]   width         数据源宽
* @param[in]   height        数据源高
* @param[in]   type          数据源类型，当前支持Trro_ColorYUVI420 Trro_ColorJPEG Trro_ColorYUYV
* @param[in]   dataSize      数据大小，为0时会自动根据格式计算大小，发送JPEG等无特定大小数据时需指定
* @param[in]   text          图像要叠加字符串(experimental)
* @param[in]   point_x       叠加文字起始x坐标，最左侧为0 (experimental)
* @param[in]   point_y       叠加文字起始y坐标，最顶部为0 (experimental)
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT DEPRECATED int TRRO_externalVideoData(int stream_id, const char * data, int width, int height, int type, int dataSize = 0, const char* text = "", int point_x = 0, int point_y = 0);

struct TRRO_TextFormat {
    const char* text = NULL;                    //图像要叠加文字内容
    int point_x = 0;                            //叠加文字起始x坐标，最左侧为0
    int point_y = 0;                            //叠加文字起始y坐标，最顶部为0
    int text_border_size = 0;                   //文字边框大小，最小为0，最大值为3
    int text_color[4] = { 255 };                  //叠加文字颜色，BGRA 0~255
    int text_border_color[4] = { 0 };           //叠加文字边框颜色，BGRA 0~255
};
/**
* @name   TRRO_externalVideoDataWithText
* @brief  外部图像输入接口
* @param[in]   stream_id     流ID
* @param[in]   data          消息体
* @param[in]   width         数据源宽
* @param[in]   height        数据源高
* @param[in]   type          数据源类型，当前支持Trro_ColorYUVI420 Trro_ColorJPEG Trro_ColorYUYV
* @param[in]   dataSize      数据大小，为0时会自动根据格式计算大小，发送JPEG等无特定大小数据时需指定
* @param[in]   textFormat    图像要叠加字符串格式，包括了文字内容，起始坐标，文字颜色，边框颜色(experimental)          
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_externalVideoDataWithText(int stream_id, const char * data, int width, int height, int type, int dataSize = 0, TRRO_TextFormat* text_format = NULL);

/**
* @name TRRO_externalEncodeVideoData
* @brief 外部编码流输入，编码流codec需要与配置codec一致
* @param[in]    stream_id            流ID
* @param[in]    data                 消息体
* @param[in]    width                数据源宽
* @param[in]    height               数据源高
* @param[in]    size                 数据大小
* @param[in]    type                 数据源类型，参考FrameType
* @return  1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_externalEncodeVideoData(int stream_id, const char * data, int width, int height, int size, FrameType type);


/**
 * @name  TRRO_setOperationPermission
 * @brief 设置远端设备操控权限，目前同时只能有一个远端设备有master权限，若已有远端设备是master权限，调用该接口设置master权限，会自动取消之前设备的master权限然后设置新设备；
 * @param[in]  remote_devid         设置权限的对端设备id
 * @param[in]  permission           参考 TrroPermission， 0 guest，只有观看权、1 master， 完全控制权限
 * @return 1 for success, other failed
 */
extern "C" TRRO_EXPORT int TRRO_setOperationPermission(const char* remote_devid, int permission);


/**
* @name TRRO_registerMultiNetworkStatsCallback
* @brief 注册多网网卡状态回调
* @param[in]   context              上下文指针，回调时会返回该上下文指针
* @param[in]   callback             回调函数
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerMultiNetworkStatsCallback(void* context, TRRO_onMultiNetworkStat * callback);

/**
* @name TRRO_registerControlDataCallback
* @brief 注册远端设备消息回调函数
* @param[in]   context              上下文指针，回调时会返回该上下文指针
* @param[in]   callback             回调函数
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerControlDataCallback(void* context, TRRO_onControlData * callback);

/**
* @name  TRRO_registerVideoCaptureCallback
* @brief 注册视频采集数据回调函数
* @param[in]   context              上下文
* @param[in]   callback             回调函数
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerVideoCaptureCallback(void* context, TRRO_onVideoCaptureData * callback);

/**
* @name TRRO_registerEncodeFrameInfoCallback
* @brief 注册编码建议信息回调函数
* @param[in]    context              上下文
* @param[in]    callback             回调函数
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerEncodeFrameInfoCallback(void *context, TRRO_onEncodeFrameInfo *callback);


/**
* @name TRRO_registerRemoteMixAudioFrameCallback
* @brief 注册远端混音音频数据回调函数
* @param[in]    context              上下文
* @param[in]    callback             回调函数
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerRemoteMixAudioFrameCallback(void* context, TRRO_onRemoteMixAudioFrame * callback);

/**
* @name TRRO_registerOnState
* @brief 注册视频连接状态回调函数
* @param[in]   context              上下文
* @param[in]   callback             回调函数
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerOnState(void* context, TRRO_OnState * callback);

/**
* @name TRRO_registerOnErrorEvent
* @brief 注册视频连接状态回调函数
* @param[in] context              上下文
* @param[in] callback             回调函数
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerOnErrorEvent(void* context, TRRO_OnErrorEvent * callback);

/**
* @name  TRRO_registerLogCallback
* @brief 注册日志回调函数
* @param[in]   context              上下文
* @param[in]   callback             回调函数
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerLogCallback(void *context, TRRO_OnLogData *callback);

/**
* @name TRRO_registerLatencyCallback
* @brief 注册时延回调函数
* @param[in]   context              上下文
* @param[in]   callback             回调函数
* @return  1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerLatencyCallback(void *context, TRRO_onLatencyReport *callback);

/**
* @name  TRRO_registerMediaState
* @brief 注册网络状态
* @param[in]   context              上下文
* @param[in]   callback             回调函数
* @return  1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerMediaState(void* context, TRRO_onMediaState * callback);

/**
* @name  TRRO_registerMediaState
* @brief 注册音频状态回调
* @param[in]   context              上下文
* @param[in]   callback             回调函数
* @return  1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerAudioMediaState(void* context, TRRO_onMediaState * callback);

/**
* @name TRRO_testNetworkQuality
* @brief 评估网络状态                注意：此函数是阻塞函数
*                                   如果网络未连接成功超时时间为10s 再加网络探测时间
* @param[in]   stream_ids           想要进行网络探测的流ID数组
* @param[in]   stream_size          想要进行网络探测的流ID数组的大小
* @param[in]   test_time            连接成功后的探测持续时间，test_time 最小2s，最大10s；
*
* @return int 网络评估 0：无法评估网络，1：良好网络，2：较差网络，3：不可用网络
*/
extern "C" TRRO_EXPORT int TRRO_testNetworkQuality(int* stream_ids, int stream_size, int test_time);

/**
* @name   TRRO_registerSignalStateCallback
* @brief  注册信令服务连接状态回调
* @param[in]   context              上下文
* @param[in]   callback             回调函数
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerSignalStateCallback(void *context, TRRO_onSignalState *callback);


/**
* @name  TRRO_registerOperationPermissionRequest
* @brief 注册远端设备操控权限请求通知回调
* @param[in]   context              上下文
* @param[in]   callback             回调函数
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_registerOperationPermissionRequest(void *context, TRRO_onOperationPermissionRequest *callback);


/**
* @name TRRO_startRecorder(Experimental)
* @brief 启动录制
* @param[in]   recorderID           录制ID (若想录制采集流，id需设置成对应stream， config文件中stream_config需加上 “record_on”:1)
* @param[in]   format               录制格式：0 ：264
* @param[in]   width                编码宽
* @param[in]   heigh                编码高
* @param[in]   jump                 录制跳帧数（隔几帧跳一帧）
* @param[in]   fps                  编码帧率
* @param[in]   bps                  码率
* @param[in]   filename             文件名
* @param[in]   config               录制选项（保留）
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_startRecorder(int recorderID, int format, int width, int heigh, int jump, int fps, int bps,
                                  const char* filename,  const char* config);

/**
* @name TRRO_sendRecordVideoData(Experimental)
* @brief 发送录制数据
* @param[in]   recorderID           录制ID
* @param[in]   data                 录制数据
* @param[in]   width                数据源宽
* @param[in]   heigh                数据源高
* @param[in]   size                 录制数据大小
* @param[in]   format               视频源格式 1 yuv420 , 4 YUYV
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_sendRecordVideoData(int recorderID, const char* data, int width, int height, int format);

/** 
 * @name    TRRO_switchRecorderFile(Experimental)
 * @brief   切换录制文件
 * @param[in]    recorderID     录制ID
 * @param[in]    filname        文件名
 * @return   1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_switchRecorderFile(int recorderID, const char* filename);

/**
* @name   Trro_Linux_stopRecorder(Experimental)
* @brief  停止录制
* @param[in]   recorderID      录制ID
* @return  1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_stopRecorder(int recorderID);

/**
* @name  TRRO_externalVideoDataNv(Experimental)
* @brief  外部码流输入-编码流，用于NV jetson平台加速 
* @param[in]   stream_id            流ID
* @param[in]   data                 消息体
* @param[in]   real_width           数据源宽
* @param[in]   real_height          数据源高
* @param[in]   size                 数据大小
* @param[in]   type                 数据源类型，参考Color类型，支持YUYV格式
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_externalVideoDataNv(int stream_id, const char * data, int real_width, int real_height, int type);

/**
 * @name TRRO_externalVideoDataDmaNative(Experimental)
 * @brief nvidia jetson平台特殊输入接口(Experimental)
 * @param[in]   stream_id 流id
 * @param[in]   fd        输入句柄
 * @param[in]   real_width     原始数据宽
 * @param[in]   real_height    原始数据高
 * @param[in]   type      输入类型
 * @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_externalVideoDataDmaNative(int stream_id, int fd, int real_width, int real_height, int type);

/**
* @name  TRRO_externVideoMJPEGDecode(Experimental)
* @brief 外部编码流输入MJPEG，使用nvidia jetson平台解码
* @param[in]   stream_id  流id
* @param[in]   data       源数据
* @param[in]   data_size  数据大小
* @param[in]   widht      原始数据宽
* @param[in]   height     原始数据高
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_externVideoMJPEGDecode(int stream_id, const char* data, int data_size, int width, int height);

/**
* @name  TRRO_externAudioData(Experimental)
* @brief 外部音频数据输入(pcm数据), 16位音频采样
* @param[in]   data         源数据
* @param[in]   data_size    数据大小
* @param[in]   channel      音频声道数
* @param[in]   sample_rate  音频采样率
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_externAudioData(const char* data, int data_size, int channel, int sample_rate);


/**
* @name  TRRO_audioMute(Experimental)
* @brief Mute 拉流端的音频 仅Server模式
* @param[in] userid  拉流端id
* @param[in] mute    是否mute
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_audioMute(const char* userid, bool mute);

/**
* @name  TRRO_reinitRtc(Experimental)
* @brief 重配置rtc，当前仅支持重置外采
* @param[in] config   重配置json数据
*/
extern "C" TRRO_EXPORT int TRRO_reinitRtc(const char * config);

/**
* @name  getErrorMsg
* @brief 根据错误码，返回错误信息。
* @param[in] errorCode   错误码
* @return errorMsg   排查帮助信息
*/
extern "C" TRRO_EXPORT const char* getErrorMsg(int errorCode);

/**
* @name  getSdkVersion
* @brief 获取sdk版本信息
* @param[in] void
* @return version   版本号
*/
extern "C" TRRO_EXPORT const char* TRRO_getSdkVersion();

/**
* @name  TRRO_getDeviceCount(Experimental)
* @brief 根据MediaDeviceType 查询音频设备的个数。
* @param[in] type  音频设备类型
* @return 设备个数
*/
extern "C" TRRO_EXPORT int TRRO_getDeviceCount(MediaDeviceType type);

/**
* @name  TRRO_getDeviceName(Experimental)
* @brief 根据MediaDeviceType 和 index查询设备名字。
* @param[in] type  设备类型
* @param[in] index 为设备索引，值为 [0, TRRO_getDeviceCount)
* @return 设备名字，失败返回null
*/
extern "C" TRRO_EXPORT const char* TRRO_getDeviceName(MediaDeviceType type, int index);

/**
* @name  TRRO_setCurrentDevice(Experimental)
* @brief 根据MediaDeviceType 和 index设备当前采集或者播放设备。
* @param[in] type  设备类型
* @param[in] index 为设备索引，值为 [0, TRRO_getDeviceCount)
* @return 1 for success, other failed
*/
extern "C" TRRO_EXPORT int TRRO_setCurrentDevice(MediaDeviceType type, int index);

/**
* @name  TRRO_startVideoCapture
* @brief 开始摄像头采集
* @param[in] context   上下文
* @param[in] url       采集路径，摄像头为/dev/video*, rtsp时是rtsp的地址
* @param[in] protocol  当等于kV4L2_DMA或者kV4L2_MMAP时，为摄像头采集。当等于 kRTSP 时，为rtsp地址
* @param[in] TrroColor 采集视频格式
* @param[in] width     采集视频宽度
* @param[in] height    采集视频高度
* @param[in] fps       采集视频帧率
* @param[in] callback  采集视频回调
* @param[in, out] capture_id 采集流的唯一标识符(重复则返回错误)，支持传入传出(当(*capture_id) > 0时才用传入值，为0则内部生成修改该值)
* @return 开始采集失败则返回错误码，返回1表示成功
*/
extern "C" TRRO_EXPORT int TRRO_startVideoCapture(void *context, const char* url, VideoCaptureProtocol protocol, TrroColor color_format, int width, int height, int fps, TRRO_onVideoCaptureFrame callback, unsigned long long* capture_id);

/**
* @name  TRRO_stopVideoCapture
* @brief 停止摄像头采集
* @param[in] capture_id 采集视频源ID(不能为0)
* @return 停止采集失败则返回错误码，返回1表示成功
*/
extern "C" TRRO_EXPORT int TRRO_stopVideoCapture(unsigned long long capture_id);


struct TRRO_RoiRect {
  float x0 = 0;                         //左上角的点坐标 取值范围0 ~ 1该值为整个画面的相对位置，实际位置为encode_width * x
  float y0 = 0;                         //计算方式同上
  float x1 = 0;                         //右下角的点坐标 计算方式同上
  float y1 = 0;                         //右下角的点坐标 计算方式同上
  int qp_delta = 0;                     //该区域与底图的qp差距
};


/**
* @name  TRRO_SetEncodeConfig
* @brief 设置编码器相关配置
* @param[in]     stream_id      视频流id
* @param[in]     roi_rects      对应的Roi区域数组
* @param[in]     len            TRRO_RoiRect数组长度
* @return 设置失败则返回错误，返回1表示成功
*/
extern "C" TRRO_EXPORT int TRRO_setEncodeRoi(int stream_id, TRRO_RoiRect* roi_rects, int len);

#endif
