#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <thread>
#include "trro_field.h"
#include <map>
#include <mutex>
#include <condition_variable>
#include <chrono>

static std::map<int, std::string> g_Record_Files;
std::mutex retry_mtx; 
std::condition_variable retry_cv;
#define MAX_RETRY 3 // maximum retry times for license check error 

static inline long long GetTime2() {

	auto now = std::chrono::system_clock::now();
	auto duration = now.time_since_epoch();
	auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();

	return millis;
}

void onControlData(void * context, const char* controlid, const char* msg, int len, int cmd) {
	
	printf("received controller msg: %s\n len %d qos:%d\n", msg, len, cmd);
	std::string out(msg);
	auto pos = out.find_last_of(':');
    if (pos != std::string::npos) {
        std::string old = out.substr(pos + 1, out.length());
        long long oldtime = std::atoll(old.c_str());
        long long newtime = GetTime2();
    } 

	TRRO_sendControlData(msg, len, cmd);
}

void OnConnectState(void* context, int stream_id, int state) {
	printf("stream_id: %d, state: %d\n", stream_id, state);
}

void externalOutYuvBuffer(const char* filename, int id) {
	int data_size = 1280*720*3/2;
	int data_width = 1280;
	int data_height = 720;
	FILE *yuv_file = fopen(filename, "rb+");
	char *data = (char*)malloc(data_size);
	memset(data, 0, data_size);
	TRRO_setChineseFontAndSize("./simhei.ttf", 40, "helo");
	while(true) {
		if(yuv_file == nullptr) {
			return;
		}
		
		int size = fread(data, 1, data_size, yuv_file);
		if (size < 1280) {
			fseek(yuv_file, 0 , SEEK_SET);
			fread(data, 1, data_size, yuv_file);
		}
		TRRO_TextFormat format;
		format.text = "hello";
		format.point_x = data_width / 2;
		format.point_y = data_height / 2;
		format.text_color[0] = 0;
		format.text_color[1] = 0;
		format.text_color[2] = 255;
		format.text_color[3] = 0;
		format.text_border_color[0] = 0;
		format.text_border_color[1] = 0;
		format.text_border_color[2] = 255;
		format.text_border_color[3] = 0;
		format.text_border_size = 1;
		TRRO_externalVideoDataWithText(id, data, data_width, data_height, 0, 0, &format);
		usleep(33 * 1000);
	}
	if (yuv_file) {
		fclose(yuv_file);
	}
	free(data);
}


int main() {
	TRRO_registerSignalStateCallback(nullptr, [](void *context, SignalState state) {
		if(state == kTrroReady) {
			printf("TRRO_init >> init success \n");
			TRRO_registerControlDataCallback(nullptr, onControlData);
			TRRO_registerOnState(nullptr, OnConnectState);
			TRRO_registerOnErrorEvent(nullptr, [](void* context, int error_code, const char* error_msg) {
				printf("error_code %d, error_msg %s\n", error_code, error_msg);
			});

			TRRO_registerVideoCaptureCallback(nullptr, [](void *context, const char* data, int width, int height, int type, int stream_id) {});
			TRRO_registerLatencyCallback(nullptr, [](void *context, int stream_id, int vcct){
				printf("latency stream id %d, vcct %d\n", stream_id, vcct);
			});

			TRRO_registerAudioMediaState(nullptr, [](void* context, int stream_id, int fps, int bps, int rtt, long long lost, long long packets_send, int stun) {
				printf("audio stream %d, fps %d, bps %d, rtt %d, lost %lld, packets_send %lld, stun %d\n", stream_id, fps, bps, rtt, lost, packets_send, stun);
			});

			TRRO_registerMediaState(nullptr, [](void* context, int stream_id, int fps, int bps, int rtt, long long lost, long long packets_send, int stun) {
				printf("stream %d, fps %d, bps %d, rtt %d, lost %lld, packets_send %lld, stun %d\n", stream_id, fps, bps, rtt, lost, packets_send, stun);
			});
			
			TRRO_registerOperationPermissionRequest(nullptr, [](void* context, const char* remote_devid, int permission) {
				printf("remote devid %s permission %d\n", remote_devid, permission);
			});

			TRRO_registerMultiNetworkStatsCallback(nullptr, [](void* context, const TrroMultiNetworkStats stats) {
				printf("multi network local:%s:%d extern:%s:%d rtt %f lost %f recv %ld send %ld\n", 
					stats.local_ip, stats.local_port, stats.extern_ip, stats.extern_port, stats.rtt, stats.lost, stats.recv_bytes, stats.send_bytes);
			});

			TRRO_registerRemoteMixAudioFrameCallback(nullptr, [](void* context, const char* data, int length, int channels, int sample_rate) {
				printf("remote mix audio frame length %d, sample_rate %d, channels %d\n", length, sample_rate, channels);
			});
			
			retry_cv.notify_one(); //server connect access, notify to call trro_start 
		} else if(state == kTrroAuthFailed) {
			printf("device_id or password is incorrect\n");
		} else if(state == kTrroKickout) {
			printf("mqtt kickout, stop sdk\n");
		} else if(state == kTrroLost) {
			printf("disconnected , connecting...  \n");
		} else if(state == kTrroReup) {
			printf("reconnect sucess\n");
		}
	});

	// using aysnc mode to init sdk and wait TRRO_registerSignalStateCallback
	int ret = TRRO_initGwPathWithLicense("./config.json", "./license.txt", -1);
	if(TRRO_SUCCED != ret) {
		const char* init_msg = getErrorMsg(ret);
		printf("Trro_init >> %s, ret: %d\n", init_msg, ret);
	}

 	{
		// wait for connected successfully callback notify
        std::unique_lock<std::mutex> lock(retry_mtx);
		retry_cv.wait(lock);

		// trro_start and retry when license check fails
		int retryCount = 0; 
	
		while (retryCount < MAX_RETRY) {
			int ret = TRRO_start();
			if(ret == TRRO_SUCCED) {
				const char* start_msg = getErrorMsg(ret);
				printf("TRRO_start >> %s\n", start_msg);
				break; 
			} else if(ret == -TRRO_INIT_PUBLIC_LICENSE_CHECK_TIMEOUT) {
				retryCount++; 
				printf("TRRO_start >> License check timeout, reconnecting count: %d\n", retryCount);
				sleep(1);
			} else {
				const char* start_msg = getErrorMsg(ret);
				printf("TRRO_start >> %s, ret: %d\n", start_msg, ret);
				break;
			}
		}
		if(retryCount == MAX_RETRY) {
			printf("TRRO_start >> License check timeout, reconnecting failed\n");
		}
        
    }

	const char* ver = TRRO_getSdkVersion();
	printf("sdk version is %s\n", ver);

    //optionally test the network
	// std::thread thread1([] {
	// 	sleep(5);
	// 	int i = 0;
	// 	int ret = TRRO_testNetworkQuality(&i, 1, 0);
	// 	printf("TRRO_testNetworkQuality ret = %d\n", ret);
	// });

	/* input YUV data to SDK for video transmission, the stream should be configured with protocol outside*/
    // std::thread t1(externalOutYuvBuffer, "./720p_30.yuv", 0);
    // t1.detach();

    // manually use the capture api to get camera data and input to SDK, the stream should be configured with protocol outside
	// note that the SDK can automatically capture and trasmit if the stream is configured with protocol v4l2 
	// unsigned long long capture_id = 0;
	// TRRO_startVideoCapture(nullptr, "/dev/video8", (VideoCaptureProtocol)1, (TrroColor)4, 1920, 1080, 30, 
	// 	[](void *context, unsigned long long capture_id, const char* data, int length, int width, int height, TrroColor color_format){
	// 		TRRO_externalVideoData(0, data, width, height, color_format);
	// 	}, 
	// &capture_id);

    while(true){
        sleep(30000);
    }
	return 0;

}


