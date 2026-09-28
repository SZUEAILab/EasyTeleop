# coding=utf-8

import ctypes
import time
from ctypes import *
import cv2
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(BASE_DIR, "sdk_lib", "libtrro_field.so")
trro_dll = ctypes.CDLL(lib_path)

isTrroInit = False

VIDEO_DEVICE = "/dev/video2"
FRAME_WIDTH  = 1280
FRAME_HEIGHT = 720
TARGET_FPS   = 30

# 图像类型枚举：按你给的定义 0=YUVI420, 4=YUYV, 5=JPEG, 21=RGB, 22=BGR
TYPE_I420 = 0
TYPE_YUYV = 4

@CFUNCTYPE(None, c_void_p, c_int)
def OnSignalConnectionState(context, signal_state):
    if signal_state == 0:
        print("init success, try to start trro")
        trro_dll.TRRO_registerControlDataCallback(None, OnControlData)
        trro_dll.TRRO_registerOnState(None, OnVideoConnectionState)
        trro_dll.TRRO_registerMediaState(None, OnMediaState)
        trro_dll.TRRO_registerOnErrorEvent(None, OnErrorEvent)
        ret = trro_start()
        print(f"start trro ret {ret}")
        if ret>0:
            global isTrroInit
            isTrroInit = True
    if signal_state == 1:
        print("network connection lost and try to reconnect")
    if signal_state == 2:
        print("reconnect success")
    if signal_state == 3:
        print("kick out by other device")
    if signal_state == 4:
        print("error password or deviceid")

@CFUNCTYPE(None, c_void_p, c_int, c_int)
def OnVideoConnectionState(context, streamid, state):
    if state == 0:
        connection = "disconnected"
    elif state == 1:
        connection = "connecting"
    elif state == 2:
        connection = "connected" 
    elif state == 3:
        connection = "disconnecting"   
    print(f"stream {streamid} video connection state is {state},  {connection}")



@CFUNCTYPE(None, c_void_p, c_int, c_int, c_int, c_int, c_int, c_int, c_int)
def OnMediaState(context, streamid,fps, bps,rtt, lost, packets, stun):
    print(f"stream {streamid}, fps {fps}, bps {bps}bps, rtt {rtt}ms, lost {lost/255.0}%, packets_send {packets}, stun {stun}")


@CFUNCTYPE(None, c_void_p, c_char_p, ctypes.POINTER(c_byte), c_int, c_int)
def OnControlData(context, controlid, msg, length, qos):
    control_str = controlid.decode('utf-8')
    msg_str = string_at(msg,length).decode('utf-8')
    print(f"receive the msg from control {control_str}: {msg_str}")


@CFUNCTYPE(None, c_void_p, c_int, c_char_p)
def OnErrorEvent(context, errorcode, msg):
    msg_str = msg.decode('utf-8')
    print(f"error_code {errorcode}, error_msg " + msg_str)

def trro_start():
    trro_dll.TRRO_start.restype = c_int
    return trro_dll.TRRO_start()


def trro_init(config_path):
    trro_dll.TRRO_initGwPath.argtypes=[c_char_p, c_int]
    trro_dll.TRRO_initGwPath.restype=c_int
    return trro_dll.TRRO_initGwPath(config_path.encode('utf-8'),-1)


def trro_destroy():
    trro_dll.TRRO_stop()


def trro_sendControlData(msgbytes, length, qos):
    trro_dll.TRRO_sendControlData.argtypes=[ctypes.POINTER(ctypes.c_byte), c_int, c_int]
    trro_dll.TRRO_sendControlData.restype=ctypes.c_int
    data = ctypes.cast(msgbytes,ctypes.POINTER(ctypes.c_byte))
    return trro_dll.TRRO_sendControlData(data,length, qos)

# color_format refer to header file,  e.g.  5  jpg,  0  I420  1 RGB 2 BGR
# stream protocol in config.json should be outside when using external video data
def trro_sendVideoData(streamid, imagebytes, length, width, height, color_format):
    trro_dll.TRRO_externalVideoData.argtypes=[c_int, ctypes.POINTER(ctypes.c_byte), c_int, c_int, c_int, c_int, c_char_p, c_int, c_int]
    trro_dll.TRRO_externalVideoData.restype=ctypes.c_int
    data = ctypes.cast(imagebytes,ctypes.POINTER(ctypes.c_byte))
    return trro_dll.TRRO_externalVideoData(streamid, data, width, height, color_format, length, "".encode('utf-8'),0,0)

def open_camera(device, width, height, fps):
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"ERROR: cannot open camera {device}")
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS,          fps)
    # 要求驱动输出 YUYV（可能被驱动忽略，OpenCV仍返回BGR，这没关系，我们用BGR→I420）
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
    # 如需尝试拿 raw YUYV，可启用：cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
    return cap

def grab_i420_frame(cap, width, height):
    ok, frame = cap.read()
    if not ok:
        return None
    # 大多数情况下 OpenCV 给到的是 BGR，这里直接 BGR→I420
    if frame.ndim == 3 and frame.shape[2] == 3:
        if frame.shape[1] != width or frame.shape[0] != height:
            frame = cv2.resize(frame, (width, height))
        i420 = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)
        return i420.tobytes()
    # 如果你关闭 CONVERT_RGB 且驱动真的给 raw YUYV，可用下面两行替换实现更省拷贝：
    # yuyv = frame.reshape(height, width, 2)
    # i420 = cv2.cvtColor(yuyv, cv2.COLOR_YUV2I420_YUY2).tobytes()
    return None

if __name__ == '__main__':
    try:
        
        trro_dll.TRRO_registerSignalStateCallback(None, OnSignalConnectionState)
        print("try to init trro")
        trro_init("./config.json")

        while(not isTrroInit):
            print("wait for TRRO START")
            time.sleep(5)

        cap = open_camera(VIDEO_DEVICE, FRAME_WIDTH, FRAME_HEIGHT, TARGET_FPS)
        if cap is None:
            raise RuntimeError("camera open failed")

        width = FRAME_WIDTH
        height = FRAME_HEIGHT
        frame_interval = 1.0 / max(1, TARGET_FPS)

        # width = 1280
        # height = 720
        # imagebytes = bytes(width*height*3//2)
        #msg = "Hello World".encode('utf-8')

        while(True):
            payload = grab_i420_frame(cap, width, height)
            if payload is None:
                print("WARN: grab frame failed")
                time.sleep(0.005)
                continue
            #trro_sendControlData(msg, len(msg), 0)
            buf = (ctypes.c_byte * len(payload)).from_buffer_copy(payload)
            ret = trro_sendVideoData(0, buf, len(payload), width, height, TYPE_I420)

            if ret <= 0:
                print(f"TRRO_externalVideoData failed, ret={ret}")
            time.sleep(frame_interval)

            # trro_sendVideoData(0, imagebytes, len(imagebytes), width, height, 0)
            # time.sleep(0.1) 
            
    finally:
        try:
            if 'cap' in locals() and cap is not None:
                cap.release()
        except Exception:
            pass
        trro_destroy()
        print("exit trro")

    
