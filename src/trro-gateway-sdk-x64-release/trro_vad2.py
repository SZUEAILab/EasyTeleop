# coding=utf-8

import ctypes
import time
from ctypes import *
import cv2
import numpy as np
import os
import json
import threading
import struct

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(BASE_DIR, "sdk_lib", "libtrro_field.so")
trro_dll = ctypes.CDLL(lib_path)

isTrroInit = False

# 默认值
DEFAULT_FRAME_WIDTH  = 1280
DEFAULT_FRAME_HEIGHT = 720
DEFAULT_TARGET_FPS   = 30

# 图像类型
TYPE_I420 = 0
TYPE_YUYV = 4

# ====== 控制/数据通道常量 ======
FRAME_BYTES   = 1024
HDR_FMT       = "<H B B B B I Q H"  # magic, ver, role, type, rsv, seq, ts_ms, payload_len
HDR_SIZE      = struct.calcsize(HDR_FMT)  # 20
MAGIC         = 0xA15A
PROTO_VER     = 1
ROLE_FIELD    = 1
MSG_DATA      = 0
TYPE_ACK      = 99
TYPE_STAT     = 2         # 现场→远端：回报“远端→现场 单向时延”（payload=<I:ms>)
TYPE_SYNC_REQ = 10        # 远端→现场：对时请求（payload=<Q:t0>)
TYPE_SYNC_RSP = 11        # 现场→远端：对时应答（payload=<Q Q Q: t0,t1,t2>)
SEND_HZ       = 100
PERIOD_S      = 1.0 / SEND_HZ
PAYLOAD_MAX   = FRAME_BYTES - HDR_SIZE  # 1004

# 统计：远端→现场 单向时延（由现场端在接收远端帧时计算）
latest_r2f_oneway_ms = 0
latest_r2f_lock = threading.Lock()

# -------------------- 回调 --------------------
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
    if   state == 0: connection = "disconnected"
    elif state == 1: connection = "connecting"
    elif state == 2: connection = "connected"
    elif state == 3: connection = "disconnecting"
    print(f"stream {streamid} video connection state is {state},  {connection}")

@CFUNCTYPE(None, c_void_p, c_int, c_int, c_int, c_int, c_int, c_int, c_int)
def OnMediaState(context, streamid,fps, bps,rtt, lost, packets, stun):
    print(f"stream {streamid}, fps {fps}, bps {bps}bps, rtt {rtt}ms, lost {lost/255.0}%, packets_send {packets}, stun {stun}")

def _ms_now():
    return int(time.time()*1000)

def _pack_hdr(mtype:int, seq:int, payload_len:int, ts_ms:int=None):
    if ts_ms is None:
        ts_ms = _ms_now()
    return struct.pack(HDR_FMT, MAGIC, PROTO_VER, ROLE_FIELD, mtype, 0, seq, ts_ms, payload_len)

@CFUNCTYPE(None, c_void_p, c_char_p, ctypes.POINTER(c_byte), c_int, c_int)
def OnControlData(context, controller_id, msg_ptr, length, qos):
    """ 现场端收到远端的数据帧：统计远端→现场 单向时延；对 TYPE_SYNC_REQ 立即应答 """
    cid = controller_id.decode('utf-8') if controller_id else "unknown"
    data = ctypes.string_at(msg_ptr, length)
    if length >= HDR_SIZE:
        magic, ver, role, mtype, rsv, seq, ts_ms, plen = struct.unpack(HDR_FMT, data[:HDR_SIZE])
        if magic == MAGIC and ver == PROTO_VER and plen <= PAYLOAD_MAX and length == FRAME_BYTES:
            now_ms = _ms_now()
            if mtype == TYPE_SYNC_REQ and plen >= 8:
                # 远端发来 t0（remote send time，Q）
                t0, = struct.unpack("<Q", data[HDR_SIZE:HDR_SIZE+8])
                t1 = now_ms  # 现场收到时间
                # 构造应答：t0,t1,t2（t2=发送应答时刻）
                t2 = _ms_now()
                payload = struct.pack("<QQQ", t0, t1, t2)
                hdr = _pack_hdr(TYPE_SYNC_RSP, seq, len(payload))
                frame = hdr + payload + b'\x00'*(FRAME_BYTES - HDR_SIZE - len(payload))
                buf = (ctypes.c_byte * FRAME_BYTES).from_buffer_copy(frame)
                _ = trro_sendControlData(buf, FRAME_BYTES, 1)  # 广播即可
                print(f"[FIELD SYNC] rsp t0={t0} t1={t1} t2={t2}")
                return

            # 普通业务帧/其他：记录远端→现场 单向时延
            oneway = now_ms - ts_ms
            with latest_r2f_lock:
                global latest_r2f_oneway_ms
                latest_r2f_oneway_ms = max(0, int(oneway))
            print(f"[FIELD RX] from {cid} seq={seq} type={mtype} qos={qos} oneway={oneway}ms len={length}")
            return
    print(f"[FIELD RX] from {cid} raw_len={length} qos={qos}")

@CFUNCTYPE(None, c_void_p, c_int, c_char_p)
def OnErrorEvent(context, errorcode, msg):
    msg_str = msg.decode('utf-8')
    print(f"error_code {errorcode}, error_msg " + msg_str)

# -------------------- TRRO 封装 --------------------
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

def trro_sendVideoData(streamid, imagebytes, length, width, height, color_format):
    trro_dll.TRRO_externalVideoData.argtypes=[c_int, ctypes.POINTER(ctypes.c_byte), c_int, c_int, c_int, c_int, c_char_p, c_int, c_int]
    trro_dll.TRRO_externalVideoData.restype=ctypes.c_int
    data = ctypes.cast(imagebytes,ctypes.POINTER(ctypes.c_byte))
    return trro_dll.TRRO_externalVideoData(streamid, data, width, height, color_format, length, "".encode('utf-8'),0,0)

# ================= 现场端 → 所有远端：数据泵（100Hz） =================
class DataPumpField(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self._stop = threading.Event()
        self.seq = 1
        self.period = PERIOD_S

    def pack_frame(self, payload: bytes, mtype=MSG_DATA) -> bytes:
        if len(payload) > PAYLOAD_MAX:
            payload = payload[:PAYLOAD_MAX]
        hdr = _pack_hdr(mtype, self.seq, len(payload))
        frame = hdr + payload + b'\x00'*(FRAME_BYTES - len(hdr) - len(payload))
        return frame

    def run(self):
        next_t = time.monotonic()
        base = b'D' * PAYLOAD_MAX
        while not self._stop.is_set():
            now = time.monotonic()
            if now < next_t:
                time.sleep(next_t - now)
            next_t += self.period
            frame = self.pack_frame(base, MSG_DATA)
            buf = (ctypes.c_byte * FRAME_BYTES).from_buffer_copy(frame)
            rc = trro_sendControlData(buf, FRAME_BYTES, 1)  # 广播
            if rc <= 0:
                time.sleep(0.02)
            self.seq = (self.seq + 1) & 0xFFFFFFFF or 1

    def stop(self):
        self._stop.set()

# ================= 现场端 → 所有远端：统计回报泵（1Hz） =================
class ReportPumpField(threading.Thread):
    """ 每秒回报一次 “远端→现场 单向时延” 给远端（TYPE_STAT，payload=<I:ms>) """
    def __init__(self):
        super().__init__(daemon=True)
        self._stop = threading.Event()
        self.seq = 1

    def run(self):
        while not self._stop.is_set():
            with latest_r2f_lock:
                val = latest_r2f_oneway_ms
            payload = struct.pack("<I", max(0, int(val)))  # 4 bytes
            hdr = _pack_hdr(TYPE_STAT, self.seq, len(payload))
            frame = hdr + payload + b'\x00'*(FRAME_BYTES - HDR_SIZE - len(payload))
            buf = (ctypes.c_byte * FRAME_BYTES).from_buffer_copy(frame)
            _ = trro_sendControlData(buf, FRAME_BYTES, 1)
            self.seq = (self.seq + 1) & 0xFFFFFFFF or 1
            time.sleep(1.0)

    def stop(self):
        self._stop.set()

# -------------------- 多路相机线程（保持不动） --------------------
class CameraSender(threading.Thread):
    def __init__(self, stream_id: int, url: str, width: int, height: int, fps: int):
        super().__init__(daemon=True)
        self.stream_id = stream_id
        self.url = url
        self.width = width or DEFAULT_FRAME_WIDTH
        self.height = height or DEFAULT_FRAME_HEIGHT
        self.fps = fps or DEFAULT_TARGET_FPS
        self.cap = None
        self._stop_event = threading.Event()
        self.frame_interval = 1.0 / max(1, int(self.fps))

    def open_camera(self):
        cap = cv2.VideoCapture(self.url, cv2.CAP_V4L2)
        if not cap.isOpened():
            print(f"[Stream {self.stream_id}] ERROR: cannot open camera {self.url}")
            return False
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS,          self.fps)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
        self.cap = cap
        print(f"[Stream {self.stream_id}] camera opened {self.url} {self.width}x{self.height}@{self.fps}")
        return True

    def grab_i420_frame(self):
        ok, frame = self.cap.read()
        if not ok:
            return None
        if frame.ndim == 3 and frame.shape[2] == 3:
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height))
            i420 = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)
            return i420.tobytes()
        return None

    def run(self):
        if not self.open_camera():
            return
        while not self._stop_event.is_set():
            payload = self.grab_i420_frame()
            if payload is None:
                time.sleep(0.005)
                continue
            buf = (ctypes.c_byte * len(payload)).from_buffer_copy(payload)
            ret = trro_sendVideoData(self.stream_id, buf, len(payload), self.width, self.height, TYPE_I420)
            if ret <= 0:
                print(f"[Stream {self.stream_id}] TRRO_externalVideoData failed, ret={ret}")
            time.sleep(self.frame_interval)

    def stop(self):
        self._stop_event.set()
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass

# -------------------- 从 config.json 读取多路配置 --------------------
def load_streams_from_config(cfg_path: str):
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    streams = cfg.get("streams_config", [])
    result = []
    for i, s in enumerate(streams):
        proto = s.get("protocol")
        if isinstance(proto, str):
            if proto.lower() != "outside":
                continue
        url = s.get("url")
        if not url:
            cam_idx = s.get("camera")
            url = f"/dev/video{cam_idx}" if cam_idx is not None else "/dev/video0"
        width  = int(s.get("width",  DEFAULT_FRAME_WIDTH))
        height = int(s.get("height", DEFAULT_FRAME_HEIGHT))
        fps    = int(s.get("fps",    DEFAULT_TARGET_FPS))
        result.append({
            "stream_id": i,
            "url": url,
            "width": width,
            "height": height,
            "fps": fps
        })
    return result

# -------------------- 主流程 --------------------
if __name__ == '__main__':
    senders = []
    data_pump = None
    report_pump = None
    try:
        trro_dll.TRRO_registerSignalStateCallback(None, OnSignalConnectionState)
        print("try to init trro")
        trro_init("./config.json")

        while(not isTrroInit):
            print("wait for TRRO START")
            time.sleep(0.5)

        data_pump = DataPumpField()
        data_pump.start()

        # ★ 启动统计回报线程（1Hz）
        report_pump = ReportPumpField()
        report_pump.start()

        # 读取多路配置
        stream_cfgs = load_streams_from_config("./config.json")
        if not stream_cfgs:
            print("[MultiStream] WARN: no valid 'outside' streams found in config.json, fallback to single stream /dev/video4")
            stream_cfgs = [{
                "stream_id": 0,
                "url": "/dev/video4",
                "width": DEFAULT_FRAME_WIDTH,
                "height": DEFAULT_FRAME_HEIGHT,
                "fps": DEFAULT_TARGET_FPS
            }]

        # 启动每路相机发送线程
        for sc in stream_cfgs:
            sender = CameraSender(
                stream_id = sc["stream_id"],
                url       = sc["url"],
                width     = sc["width"],
                height    = sc["height"],
                fps       = sc["fps"]
            )
            sender.start()
            senders.append(sender)

        print(f"[MultiStream] started {len(senders)} stream(s). Press Ctrl+C to stop.")
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        pass
    finally:
        for s in senders:
            s.stop()
        for s in senders:
            s.join(timeout=2.0)
        if data_pump:
            data_pump.stop()
            data_pump.join(timeout=2.0)
        if report_pump:
            report_pump.stop()
            report_pump.join(timeout=2.0)
        trro_destroy()
        print("exit trro")
