# coding=UTF-8
import json
from collections import OrderedDict


#revise the following code paras to gen the config json file
def gen_config():

    json_data = OrderedDict()

    #public cloud or private
    public_cloud = False  # set the cloud mode

    # Chinese tencent cloud or International tencent cloud
    use_international = False

    if(public_cloud):
        if use_international: 
            json_data["cloud_mode"]="public_intl"
        else:
            json_data["cloud_mode"]="public"
        #public cloud config
        json_data["projectid"]=""                  #field project id created on cloud 
        json_data["device_id"]=""                  #field device id created on cloud 
        json_data["device_name"]=""
        json_data["password"]=""                   #field device token/password
        json_data["certificate"]="./device.pem"    #cloud certificate
        json_data["sdk_mode"]="server2"            
    else:
        json_data["cloud_mode"]="private"
        #private cloud config
        json_data["device_id"]=""                     
        json_data["device_name"]=""
        json_data["server_ip"]=""                  #private access service IP
        json_data["server_port"]=2883              #access service port
        json_data["rtc_server_ip"]=""              #rtc service IP
        json_data["rtc_server_port"]=3000          #rtc service port
        json_data["sdk_mode"]="server"             
    

    #if want to revise local port，revise here, keep port range >= 100
    port_conf = False #set the port or not
    if(port_conf):
        json_data["max_port"]=50000
        json_data["min_port"]=50100

    #if using multiple networks to transmision, revise here
    netbind_conf = False #bind target network interface or not
    if(netbind_conf):
        json_data["network_bind"]=["xx.xx.xx.xx","xx.xx.xx.xx"]  # target network interface ip; 
    
    #if using aduio，revise here
    audio_conf = False #open audio or not
    if(audio_conf):
        json_data["audio_enable"]=1   #open local audio capture
        json_data["audio_receive"]=1  #open remote audio play
    else:
        json_data["audio_enable"]=0
        json_data["audio_receive"]=0

    #log config
    json_data["log_enable"]=1  #open log，0 close 1 normal  2 debug


    #--------below is video stream configuration-----------

    video_num = 2  #video stream num, keep same size as video_arry
    json_data["device_streams"]=video_num
    video_arry=[]

    #add the video stream item
    video_arry.append(v4l2_video_item(30,1920,1080,1920,1080,2000,1000,0))         #example, add one v4l2 camera (e.g. USB/GSML camera) video
    video_arry.append(rtsp_enc_video_item(25,1920,1080,"rtsp://admin:admin@192.168.1.1/"))    #example, add one rtsp (e.g. network camera) video 

    #append v4l2 capture video， video_arry.append(v4l2_video_item(30,1920,1080,1920,1080,2000,1000,0))
    #append video with directly input YUV images，video_arry.append(outside_video_item(30,1920,1080,1920,1080,2000,1000))
    #append video with directly input encoded frame (e.g. H264/H265 with SPS/PPS for every IDR frame)，video_arry.append(outenc_video_item())
    #append rtsp video with no decoding，video_arry.append(rtsp_enc_video_item(25,1920,1080,"rtsp://admin:admin@192.168.1.1/"))
    #append rtsp video with transcode，video_arry.append(normal_url_video_item(25,1920,1080,1920,1080,2000,1000,"rtsp://admin:admin@192.168.1.1/"))
    json_data["streams_config"]=video_arry
    
    if(len(video_arry) < video_num):
        print("video_arry size is small than video_num\n")
        return

    with open('config.json','w') as f1:
        json.dump(json_data,f1,indent=2)



#v4l2 capture video stream
def v4l2_video_item(fps, width, height, encode_width, encode_height, bps, min_bps, camera_index, codec=0):
    video_item=OrderedDict()
    video_item["fps"]=fps          
    video_item["width"]=width      #capture width
    video_item["height"]=height    #capture height
    video_item["encode_width"]=encode_width     
    video_item["encode_height"]=encode_height   
    video_item["bps"]=bps                       #expect video rate, recommend 1080P 2500， 720P 2000 for H264； H265 can reduce 500 extraly
    video_item["min_bps"]=min_bps               #accpeted video rate for weak network case,  recommend 1080P 1500， 720P 1000； H265 can reduce 300 extraly
    video_item["codec"]=codec    #encode codec 0 H264  1 H265 2 av1 only for nvidia orin 
    video_item["protocol"]="v4l2"
    video_item["camera"]=camera_index # camera index, 0 for /dev/video0, x for /dev/videox
    return video_item

#external YUV images input video stream
def outside_video_item(fps,width, height, encode_width, encode_height, bps, min_bps, codec=0):
    video_item=OrderedDict()
    video_item["fps"]=fps          
    video_item["width"]=width      #input width
    video_item["height"]=height    #input height
    video_item["encode_width"]=encode_width     
    video_item["encode_height"]=encode_height   
    video_item["bps"]=bps                        #expect video rate, recommend 1080P 2500， 720P 2000 for H264； H265 can reduce 500 extraly
    video_item["min_bps"]=min_bps               #accpeted video rate for weak network case,  recommend 1080P 1500， 720P 1000； H265 can reduce 300 extraly
    video_item["codec"]=codec    #encode codec 0 H264  1 H265 2 av1 only for nvidia orin 
    video_item["protocol"]="outside"
    return video_item

#external encoded video input video stream
def outenc_video_item(codec=0):
    video_item=OrderedDict()
    video_item["fps"]=30
    video_item["width"]=1920
    video_item["height"]=1080
    video_item["codec"]=codec    #encode codec 0 H264  1 H265
    video_item["protocol"]="out_enc"
    return video_item

#rtsp encoded stream input with nodecoding
def rtsp_enc_video_item(fps, width, height, rtsp_url, codec=0):
    video_item=OrderedDict()
    video_item["fps"]=fps
    video_item["width"]=width
    video_item["height"]=height
    video_item["protocol"]="rtsp_enc"
    video_item["codec"]=codec
    cameras=[]
    camera_item={}
    camera_item["protocol"]=1
    camera_item["url"]=rtsp_url
    camera_item["width"]=width
    camera_item["height"]=height
    camera_item["fps"]=fps
    cameras.append(camera_item)
    video_item["cameras"]=cameras
    return video_item

#rtsp url stream input with decoding
def normal_url_video_item(fps,width, height, encode_width, encode_height, bps, min_bps, url, codec=0):
    video_item=OrderedDict()
    video_item["fps"]=fps
    video_item["width"]=width
    video_item["height"]=height
    video_item["encode_width"]=encode_width
    video_item["encode_height"]=encode_height
    video_item["bps"]=bps
    video_item["min_bps"]=min_bps
    video_item["codec"]=codec
    video_item["protocol"]="normal"
    cameras=[]
    camera_item=OrderedDict()
    camera_item["protocol"]=1
    camera_item["url"]= url
    camera_item["width"]=width
    camera_item["height"]=height
    camera_item["fps"]=fps
    cameras.append(camera_item)
    video_item["cameras"]=cameras
    return video_item



gen_config()
