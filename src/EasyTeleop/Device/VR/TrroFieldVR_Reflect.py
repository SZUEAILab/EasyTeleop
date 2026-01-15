# EasyTeleop/Device/VR/TrroFieldVR.py
# coding: utf-8
"""
TRRO 现场端设备类（多路视频版本）
- 继承 BaseVR -> BaseDevice
- 默认读取：
    lib_path   = EasyTeleop/third-party/trro-gateway-sdk-x64-release/sdk_lib/libtrro_field.so
    config_path= EasyTeleop/third-party/trro-gateway-sdk-x64-release/config.json
- 多路视频来自 config.json.streams_config 中 protocol == "outside" 的条目
- 收到业务二进制：payload=[1B kind][1B flags][protobuf bytes…]，解析后 emit("message", {"type","payload"})
  非 JSON：emit("message", {"seq","type","qos","raw":bytes})
"""

import os
import time
import json
import struct
import ctypes
import threading
from ctypes import c_void_p, c_int, c_char_p, c_byte
from queue import Queue, Empty
from google.protobuf import json_format
from . import controller_hand_pb2 as pb 
from collections import deque
import cv2  # 现场端采集用
import zstandard as zstd
import math
import struct
# import numpy as np  # 如需图像处理可启用

from .BaseVR import BaseVR

# ========= 协议常量，保持与你 demo 一致 =========
#FRAME_BYTES   = 1024
HDR_FMT       = "<H B B B B I Q H"  # magic, ver, role, type, rsv, seq, ts_ms, payload_len
HDR_SIZE      = struct.calcsize(HDR_FMT)  # 20
MAGIC         = 0xA15A
PROTO_VER     = 1
ROLE_FIELD    = 1
MAX_PAYLOAD = 65535 

# 自定义业务类型（你已有）
MSG_DATA      = 0
TYPE_ACK      = 99
TYPE_STAT     = 2          # 现场→远端：回报“远端→现场 单向时延”（payload=<I:ms>)
TYPE_SYNC_REQ = 10         # 远端→现场：对时请求（payload=<Q:t0>)
TYPE_SYNC_RSP = 11         # 现场→远端：对时应答（payload=<Q Q Q: t0,t1,t2>)

# 采集与默认
DEFAULT_FRAME_WIDTH  = 1280
DEFAULT_FRAME_HEIGHT = 720
DEFAULT_TARGET_FPS   = 30

# 视频颜色格式（TRRO 定义）
TYPE_I420 = 0
TYPE_YUYV = 4

# 发送节奏（数据）
SEND_HZ     = 100
PERIOD_S    = 1.0 / SEND_HZ
#PAYLOAD_MAX = FRAME_BYTES - HDR_SIZE

# ========= protobuf 定义 =========
# >>> ADD: JSON <-> Protobuf 工具
TYPE_NAME_TO_ID = {"controller": 1, "hand": 2}
TYPE_ID_TO_NAME = {v: k for k, v in TYPE_NAME_TO_ID.items()}

TYPE_TO_PBMSG = {
    "controller": pb.ControllerInput,
    "hand":       pb.HandInputCompressed,
}
def _pb_bytes_to_json_dict(type_str: str, pb_bytes: bytes,
                           include_defaults=True, preserve_names=True) -> dict:
    """
    将 protobuf 原始字节解析为 JSON dict（供 emit 使用）
    """
    pb_cls = TYPE_TO_PBMSG[type_str]
    msg = pb_cls()
    msg.ParseFromString(pb_bytes)
    js = json_format.MessageToJson(
        msg,
        including_default_value_fields=include_defaults,
        preserving_proto_field_name=preserve_names
    )
    return json.loads(js)

# ========= 内部：protobuf 转 JSON 解码函数 =========
HAND_JOINT_MAX_OFFSET = 0.2  # 要和远程端的 HAND_JOINT_MAX_OFFSET 保持一致

def _clamp(v, vmin, vmax):
    return vmin if v < vmin else (vmax if v > vmax else v)

def _decode_rel_pos_bytes(rel_bytes: bytes, max_offset=HAND_JOINT_MAX_OFFSET):
    """
    和远程端 _encode_rel_pos 反向：
      encode: struct.pack("<hhh", qx,qy,qz)，所以这里按 3 个 int16 解
    """
    if len(rel_bytes) != 6:
        return {"dx": 0.0, "dy": 0.0, "dz": 0.0}

    qx, qy, qz = struct.unpack("<hhh", rel_bytes)

    def dec(q):
        return max_offset * float(q) / 32767.0

    return {
        "dx": dec(qx),
        "dy": dec(qy),
        "dz": dec(qz),
    }

def _decode_quat_bytes(rot_bytes: bytes):
    """
    和 _encode_quat_to_u8 反向：
      t = q/255.0
      v = (t - 0.5)*2
    """
    if len(rot_bytes) != 4:
        return {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}

    qx, qy, qz, qw = rot_bytes

    def dec(q):
        t = float(q) / 255.0
        return (t - 0.5) * 2.0

    return {
        "x": dec(qx),
        "y": dec(qy),
        "z": dec(qz),
        "w": dec(qw),
    }

def _decode_finger_curls_bytes(curls_bytes: bytes):
    """
    和 _encode_finger_scalar_to_u8 反向：
      v = q / 255.0
    顺序: fullCurl, baseCurl, tipCurl, pinch, spread
    """
    if len(curls_bytes) != 5:
        return {
            "fullCurl": 0.0,
            "baseCurl": 0.0,
            "tipCurl":  0.0,
            "pinch":    0.0,
            "spread":   0.0,
        }

    bf, bb, bt, bp, bs = curls_bytes

    def dec(b):
        return float(b) / 255.0

    return {
        "fullCurl": dec(bf),
        "baseCurl": dec(bb),
        "tipCurl":  dec(bt),
        "pinch":    dec(bp),
        "spread":   dec(bs),
    }

def _decode_one_hand_pb_to_readable(hand_pb):
    """
    hand_pb: HandInputCompressed 里的 leftHand / rightHand
    还原成“人类可读的” dict：
    - rootPose.position 保持绝对坐标
    - joints.position 还原为绝对坐标 (root + offset)
    - joints.offset 保留相对偏移（可选，看你要不要）
    - rotation、fingers 都还原成 float
    """
    root_pos = hand_pb.rootPose.position
    root_rot = hand_pb.rootPose.rotation
    Rx = float(root_pos.x)
    Ry = float(root_pos.y)
    Rz = float(root_pos.z)

    out = {
        "isTracked": bool(getattr(hand_pb, "isTracked", False)),
        "rootPose": {
            "position": {"x": Rx, "y": Ry, "z": Rz},
            "rotation": {
                "x": float(root_rot.x),
                "y": float(root_rot.y),
                "z": float(root_rot.z),
                "w": float(root_rot.w),
            },
        },
        "joints": [],
        "fingers": [],
    }

    # joints
    for jc in hand_pb.joints:
        rel_bytes = bytes(jc.rel_pos)
        rot_bytes = bytes(jc.rot)

        offset = _decode_rel_pos_bytes(rel_bytes)
        rot    = _decode_quat_bytes(rot_bytes)

        jx = Rx + offset["dx"]
        jy = Ry + offset["dy"]
        jz = Rz + offset["dz"]

        out["joints"].append({
            "position": {"x": jx, "y": jy, "z": jz},  # 绝对坐标
            "offset":   offset,                       # 相对 root 的偏移（可选）
            "rotation": rot,
        })

    # fingers
    for fc in hand_pb.fingers:
        curls_bytes = bytes(fc.curls)
        curls = _decode_finger_curls_bytes(curls_bytes)
        out["fingers"].append(curls)

    return out

def decode_hand_zstd_to_readable(zstd_bytes: bytes):
    """
    现场端用：
    hand 的 pb 字节是 ZSTD 压过的 HandInputCompressed
    这里：ZSTD 解压 → ParseFromString → 还原成人可读 dict
    """
    dctx = zstd.ZstdDecompressor()
    pb_raw = dctx.decompress(zstd_bytes)

    msg = pb.HandInputCompressed()
    msg.ParseFromString(pb_raw)

    res = {}
    if msg.HasField("leftHand"):
        res["leftHand"] = _decode_one_hand_pb_to_readable(msg.leftHand)
    if msg.HasField("rightHand"):
        res["rightHand"] = _decode_one_hand_pb_to_readable(msg.rightHand)
    return res


# ========= 内部：多路相机线程 =========
class _CameraSender(threading.Thread):
    """
    每路视频一个线程：打开相机（/dev/videoX 或 URL），抓帧 → BGR 转 I420 → 调 TRRO_externalVideoData
    """
    def __init__(self, dll, stream_id: int, url: str, width: int, height: int, fps: int, stop_evt: threading.Event):
        super().__init__(daemon=True, name=f"trro-camera-{stream_id}")
        self._dll = dll
        self.stream_id = int(stream_id)
        self.url = url
        self.width = int(width) if width else DEFAULT_FRAME_WIDTH
        self.height = int(height) if height else DEFAULT_FRAME_HEIGHT
        self.fps = int(fps) if fps else DEFAULT_TARGET_FPS
        self._stop_evt = stop_evt
        self.cap = None
        self.frame_interval = 1.0 / max(1, self.fps)

    def _open_camera(self) -> bool:
        # 使用 V4L2 打开本地摄像头；若为 RTSP/HTTP 流，可去掉 CAP_V4L2
        cap = cv2.VideoCapture(self.url, cv2.CAP_V4L2)
        if not cap.isOpened():
            print(f"[Camera {self.stream_id}] ERROR: cannot open {self.url}")
            return False

        # 基本属性设置
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS,          self.fps)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))  # 仅作驱动 hint，不影响发送格式

        self.cap = cap
        print(f"[Camera {self.stream_id}] opened {self.url} {self.width}x{self.height}@{self.fps}")
        return True

    def _grab_i420_bytes(self):
        ok, frame = self.cap.read()
        if not ok:
            return None
        # frame: BGR(HxWx3)
        if frame.ndim == 3 and frame.shape[2] == 3:
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height))
            i420 = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)
            return i420.tobytes()
        return None

    def run(self):
        if not self._open_camera():
            return

        # externalVideoData(sig):
        # int TRRO_externalVideoData(int streamid, BYTE* data, int width, int height, int color_format,
        #                            int length, char* extra, int x, int y)
        while not self._stop_evt.is_set():
            payload = self._grab_i420_bytes()
            if payload is None:
                time.sleep(0.005)
                continue

            buf = (ctypes.c_byte * len(payload)).from_buffer_copy(payload)
            rc = self._dll.TRRO_externalVideoData(self.stream_id, buf, self.width, self.height, TYPE_I420, len(payload), "".encode('utf-8'), 0, 0)
            if rc <= 0:
                print(f"[Camera {self.stream_id}] TRRO_externalVideoData failed rc={rc}")
                time.sleep(0.01)
            time.sleep(self.frame_interval)

        # 收尾
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        print(f"[Camera {self.stream_id}] stopped.")

# ========= 主类：TRRO 现场端设备 =========
class TrroFieldVR(BaseVR):
    """
    现场端 TRRO 设备类（多路视频）
    """
    name = "TRRO Field VR"
    description = "TRRO-based field-side VR device (multi-stream video)"

    # 配置项：保留默认路径，但支持覆盖
    need_config = {
        "lib_path":   "str|optional: path to libtrro_field.so",
        "config_path":"str|optional: path to config.json",
        # 可选开关
        "enable_data_pump": "bool|optional: default False (100Hz demo泵，正常可关闭)",
        "send_hz": "int|optional: data send frequency, default=100",
    }

    # 默认硬编码路径（按你要求的目录）
    _DEFAULT_LIB_PATH   = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                 "../../third-party/trro-gateway-sdk-x64-release/sdk_lib/libtrro_field.so"))
    _DEFAULT_CFG_PATH   = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                 "../../third-party/trro-gateway-sdk-x64-release/config.json"))

    def __init__(self, config=None):
        super().__init__(config)

        # 发送队列（业务数据）
        self.tx_data_queue: Queue = Queue(maxsize=2000)

        # 统计：远端→现场 单向时延（ms）
        self._latest_r2f_ms = 0
        self._r2f_lock = threading.Lock()

        # 序号
        self._seq = 1

        # SDK 句柄 & 回调引用（防 GC）
        self._dll = None
        self._cb_signal = None
        self._cb_control = None
        self._cb_vstate = None
        self._cb_mstate = None
        self._cb_error = None

        # 线程/控制
        self._stop_evt = threading.Event()
        self._workers = []
        self._camera_threads = []

    # -------- BaseDevice 接口实现 --------
    def set_config(self, config: dict) -> bool:
        # 默认值
        if config is None:
            config = {}

        # 默认路径（可由调用方覆盖）
        lib_path   = self._resolve_path(config.get("lib_path")    or self._DEFAULT_LIB_PATH)
        config_path= self._resolve_path(config.get("config_path") or self._DEFAULT_CFG_PATH)

        if not os.path.isfile(lib_path):
            raise FileNotFoundError(f"TRRO so 不存在: {lib_path}")
        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"config.json 不存在: {config_path}")

        config.setdefault("enable_data_pump", False)
        config.setdefault("send_hz", SEND_HZ)

        self.config = {
            **config,
            "lib_path": lib_path,
            "config_path": config_path,
        }
        return True

    def _connect_device(self) -> bool:
        """
        连接流程：
          1) 加载 so，注册回调
          2) TRRO_initGwPath(config.json)，TRRO_start()
          3) 启动：数据发送线程、统计上报线程、多路相机线程
        """
        # 1) 加载 so & 签名
        if self._dll is None:
            self._dll = ctypes.CDLL(self.config["lib_path"])
        self._bind_sdk_signatures()

        # 2) 回调实例化（保存引用，避免被 GC）
        self._cb_signal  = ctypes.CFUNCTYPE(None, c_void_p, c_int)(self._on_signal_state)
        self._cb_control = ctypes.CFUNCTYPE(None, c_void_p, c_char_p, ctypes.POINTER(c_byte), c_int, c_int)(self._on_control_data)
        self._cb_vstate  = ctypes.CFUNCTYPE(None, c_void_p, c_int, c_int)(self._on_video_state)
        self._cb_mstate  = ctypes.CFUNCTYPE(None, c_void_p, c_int, c_int, c_int, c_int, c_int, c_int, c_int)(self._on_media_state)
        self._cb_error   = ctypes.CFUNCTYPE(None, c_void_p, c_int, c_char_p)(self._on_error_event)

        self._dll.TRRO_registerSignalStateCallback(None, self._cb_signal)
        self._dll.TRRO_registerControlDataCallback(None, self._cb_control)
        self._dll.TRRO_registerOnState(None, self._cb_vstate)
        self._dll.TRRO_registerMediaState(None, self._cb_mstate)
        self._dll.TRRO_registerOnErrorEvent(None, self._cb_error)

        # 3) init + start
        rc = self._dll.TRRO_initGwPath(self.config["config_path"].encode('utf-8'), -1)
        if rc <= 0:
            raise RuntimeError(f"TRRO_initGwPath 失败 rc={rc}")
        rc = self._dll.TRRO_start()
        if rc <= 0:
            raise RuntimeError(f"TRRO_start 失败 rc={rc}")

        # 4) 启动线程
        self._stop_evt.clear()
        self._start_workers()
        self._start_cameras_from_config()

        return True

    def _disconnect_device(self) -> bool:
        # 停数据线程
        self._stop_evt.set()
        for t in self._workers:
            t.join(timeout=2.0)
        self._workers.clear()

        # 停相机线程
        for c in self._camera_threads:
            c.join(timeout=2.0)
        self._camera_threads.clear()

        # SDK stop
        try:
            if self._dll:
                self._dll.TRRO_stop()
        except Exception:
            pass
        return True

    def _main(self):
        # 设备主循环无需繁重任务（回调+线程已处理），轻微睡眠即可
        time.sleep(0.2)

    # -------- 对外方法 --------
    def send_data(self, obj_or_bytes, mtype=MSG_DATA, qos=1):
        """
        业务数据发送：放入队列，由发送线程统一打 HDR 后调用 TRRO_sendControlData
        """
        self.tx_data_queue.put((obj_or_bytes, int(mtype), int(qos)), block=False)

    # -------- 内部：SDK 绑定、回调、线程 --------
    def _bind_sdk_signatures(self):
        # 基本控制
        self._dll.TRRO_start.restype = c_int
        self._dll.TRRO_stop.restype  = None

        self._dll.TRRO_initGwPath.argtypes = [c_char_p, c_int]
        self._dll.TRRO_initGwPath.restype  = c_int

        # 回调注册
        self._dll.TRRO_registerSignalStateCallback.argtypes = [c_void_p, ctypes.CFUNCTYPE(None, c_void_p, c_int)]
        self._dll.TRRO_registerControlDataCallback.argtypes = [c_void_p, ctypes.CFUNCTYPE(None, c_void_p, c_char_p, ctypes.POINTER(c_byte), c_int, c_int)]
        self._dll.TRRO_registerOnState.argtypes = [c_void_p, ctypes.CFUNCTYPE(None, c_void_p, c_int, c_int)]
        self._dll.TRRO_registerMediaState.argtypes = [c_void_p, ctypes.CFUNCTYPE(None, c_void_p, c_int, c_int, c_int, c_int, c_int, c_int, c_int)]
        self._dll.TRRO_registerOnErrorEvent.argtypes = [c_void_p, ctypes.CFUNCTYPE(None, c_void_p, c_int, c_char_p)]

        # 发送函数
        self._dll.TRRO_sendControlData.argtypes = [ctypes.POINTER(c_byte), c_int, c_int]
        self._dll.TRRO_sendControlData.restype  = c_int

        self._dll.TRRO_externalVideoData.argtypes = [c_int, ctypes.POINTER(c_byte), c_int, c_int, c_int, c_int, c_char_p, c_int, c_int]
        self._dll.TRRO_externalVideoData.restype  = c_int

    # ---- 回调 ----
    def _on_signal_state(self, _ctx, signal_state: int):
        # 0:init ok  1:lost  2:reconnected  3:kick  4:bad credential
        if signal_state == 1:
            self.emit("error", "network connection lost, SDK will try reconnect")
        elif signal_state == 4:
            self.emit("error", "invalid device_id/password")

    def _on_video_state(self, _ctx, streamid: int, state: int):
        # 0:disconnected, 1:connecting, 2:connected, 3:disconnecting
        # 需要的话可以上抛状态
        pass

    def _on_media_state(self, _ctx, streamid, fps, bps, rtt, lost, packets, stun):
        # 需要的话你可以在这里 emit 统计
        # self.emit("stats", {...})
        pass

    def _on_error_event(self, _ctx, errorcode: int, msg: bytes):
        self.emit("error", f"TRRO error {errorcode}: {msg.decode('utf-8', 'ignore')}")

    def _on_control_data(self, _ctx, controller_id: bytes, msg_ptr, length: int, qos: int):
        """
        现场端收到远端帧：对时应答 & 单向时延统计；业务 payload：优先 JSON，否则 bytes 包裹
        """
        cid = controller_id.decode('utf-8') if controller_id else "unknown"
        data = ctypes.string_at(msg_ptr, length)
        # print(f"[RX] raw_len={length} first20={data[:20].hex(' ')} qos={qos}")
        if length >= HDR_SIZE:
            try:
                magic, ver, role, mtype, rsv, seq, ts_ms, plen = struct.unpack(HDR_FMT, data[:HDR_SIZE])
                # print(f"[RX] hdr magic=0x{magic:04X} ver={ver} role={role} type={mtype} seq={seq} plen={plen} len={length}")
                if length != HDR_SIZE + plen:
                    print(f"[RX] WARN length({length}) != HDR_SIZE+plen({HDR_SIZE + plen}) → 按旧条件会丢弃")
            except Exception as e:
                print(f"[RX] header unpack failed: {e}")

            valid_varlen = (length == HDR_SIZE + plen)
            valid_fixed  = False 
            if magic == MAGIC and ver == PROTO_VER and (valid_varlen or valid_fixed):
                now_ms = self._ms_now()

                # 1) 对时请求：收到远端的 t0，回 (t0,t1,t2)
                if mtype == TYPE_SYNC_REQ and plen >= 8:
                    (t0,) = struct.unpack("<Q", data[HDR_SIZE:HDR_SIZE+8])
                    t1 = now_ms
                    t2 = self._ms_now()
                    payload = struct.pack("<QQQ", t0, t1, t2)
                    frame = self._pack_frame(payload, mtype=TYPE_SYNC_RSP, seq=seq)
                    buf = (ctypes.c_byte * len(frame)).from_buffer_copy(frame)
                    _ = self._dll.TRRO_sendControlData(buf, len(frame), 1)
                    return

                # 2) 统计远端->现场 单向时延
                oneway = max(0, int(now_ms - ts_ms))
                with self._r2f_lock:
                    self._latest_r2f_ms = oneway

                # 3) 业务 payload
                payload = data[HDR_SIZE: HDR_SIZE+plen]
                if mtype == MSG_DATA:
                    # print(f"[RX] MSG_DATA plen={plen}")
                    payload = data[HDR_SIZE: HDR_SIZE+plen]
                    if plen >= 2:
                        kind  = payload[0]
                        flags = payload[1]
                        pb    = payload[2:]
                        # print(f"[RX] MSG_DATA kind={kind} flags={flags} pb_len={len(pb)}")
                        type_str = TYPE_ID_TO_NAME.get(int(kind))
                        if type_str and type_str in TYPE_TO_PBMSG:
                            try:
                                if type_str == "controller":
                                    payload_obj = _pb_bytes_to_json_dict(
                                        type_str, pb,
                                        include_defaults=True,
                                        preserve_names=True
                                    )

                                # ✨ hand：先 ZSTD 解压，再按照你远程端的量化规则还原成“人能看懂”的 dict
                                elif type_str == "hand":
                                    payload_obj = decode_hand_zstd_to_readable(pb)

                                else:
                                    # 将来如果还有其他类型，可以在这里继续分支
                                    payload_obj = _pb_bytes_to_json_dict(
                                        type_str, pb,
                                        include_defaults=True,
                                        preserve_names=True
                                    )

                                out = {"type": type_str, "payload": payload_obj, "flags": int(flags)}
                                self.data_queue.put(out)
                                self.emit("message", out)
                                return
                            except Exception as e:
                                print(f"[rx rawpb] parse failed kind={kind} ({type_str}): {e}")

                        # 未知 kind 或解析失败：兜底上抛原始二进制
                        fallback = {"seq": seq, "type": mtype, "qos": qos, "kind": int(kind), "flags": int(flags), "raw": pb}
                        self.data_queue.put(fallback)
                        self.emit("message", fallback)
                        return

                # 兜底：payload 不足 2B 或非 MSG_DATA，按原始二进制上抛
                msg = {"seq": seq, "type": mtype, "qos": qos, "raw": payload}
                self.data_queue.put(msg)
                self.emit("message", msg)
                return

        # 非我们定义的协议帧：上抛元信息
        info = {"from": cid, "raw_len": length, "qos": qos}
        self.data_queue.put(info)
        self.emit("message", info)

    # ---- 线程：数据发送、统计回报、可选数据泵、相机 ----
    def _start_workers(self):
        # 数据发送线程
        t1 = threading.Thread(target=self._tx_data_worker, name="trro-tx-data", daemon=True)
        t1.start()
        self._workers.append(t1)

        # 统计回报线程（每秒回报一次 TYPE_STAT，payload=<I:ms>）
        t2 = threading.Thread(target=self._report_pump, name="trro-report", daemon=True)
        t2.start()
        self._workers.append(t2)

        # 可选：100Hz demo 数据泵（多数场景可关闭）
        if bool(self.config.get("enable_data_pump", False)):
            t3 = threading.Thread(target=self._data_pump_100hz, name="trro-datapump", daemon=True)
            t3.start()
            self._workers.append(t3)

    def _tx_data_worker(self):
        send_hz = int(self.config.get("send_hz", SEND_HZ))
        period = 1.0 / max(1, send_hz)
        next_t = time.monotonic()
        while not self._stop_evt.is_set():
            try:
                obj_or_bytes, mtype, qos = self.tx_data_queue.get(timeout=period)
            except Empty:
                # 保持节奏
                now = time.monotonic()
                if now < next_t:
                    time.sleep(next_t - now)
                next_t += period
                continue

            # 序列化 payload
            try:
                if isinstance(obj_or_bytes, dict) and "type" in obj_or_bytes and "payload" in obj_or_bytes and isinstance(obj_or_bytes["payload"], dict):
                    type_str = obj_or_bytes.get("type")
                    payload_dict = obj_or_bytes.get("payload") or {}
                    if type_str in TYPE_TO_PBMSG:
                        # dict -> protobuf -> [kind][flags][pb]
                        pb_cls = TYPE_TO_PBMSG[type_str]
                        msg = pb_cls()
                        json_format.Parse(json.dumps(payload_dict, ensure_ascii=False), msg, ignore_unknown_fields=True)
                        pb = msg.SerializeToString()
                        kind = TYPE_NAME_TO_ID.get(type_str, 0)
                        flags = 0
                        payload = bytes([kind, flags]) + pb
                    else:
                        # 未知类型：直接原样 JSON 文本
                        payload = json.dumps(obj_or_bytes, ensure_ascii=False).encode("utf-8")

                elif isinstance(obj_or_bytes, (bytes, bytearray)):
                    payload = bytes(obj_or_bytes)

                elif isinstance(obj_or_bytes, str):
                    payload = obj_or_bytes.encode("utf-8")

                else:
                    # 其他对象：尝试转成 JSON，否则转成字符串
                    try:
                        payload = json.dumps(obj_or_bytes, ensure_ascii=False).encode("utf-8")
                    except Exception:
                        payload = str(obj_or_bytes).encode("utf-8")

            except Exception as e:
                print(f"[tx] serialize payload failed: {e}; fallback to utf-8 text")
                payload = str(obj_or_bytes).encode("utf-8")

            # 固定帧壳上限保护

            frame = self._pack_frame(payload, mtype=mtype)
            buf = (ctypes.c_byte * len(frame)).from_buffer_copy(frame)
            rc = self._dll.TRRO_sendControlData(buf, len(frame), qos if qos else 1)
            if rc <= 0:
                time.sleep(0.02)

            # 节奏
            now = time.monotonic()
            if now < next_t:
                time.sleep(next_t - now)
            next_t += period

    def _report_pump(self):
        while not self._stop_evt.is_set():
            with self._r2f_lock:
                ms = max(0, int(self._latest_r2f_ms))
            payload = struct.pack("<I", ms)
            frame = self._pack_frame(payload, mtype=TYPE_STAT)
            buf = (ctypes.c_byte * len(frame)).from_buffer_copy(frame)
            _ = self._dll.TRRO_sendControlData(buf, len(frame), 1)
            time.sleep(1.0)

    def _data_pump_100hz(self):
        base = b'D' * 800
        period = 1.0 / 100.0
        next_t = time.monotonic()
        while not self._stop_evt.is_set():
            frame = self._pack_frame(base, mtype=MSG_DATA)
            buf = (ctypes.c_byte * len(frame)).from_buffer_copy(frame)
            _ = self._dll.TRRO_sendControlData(buf, len(frame), 1)
            now = time.monotonic()
            if now < next_t:
                time.sleep(next_t - now)
            next_t += period

    def _start_cameras_from_config(self):
        cfg_path = self.config["config_path"]
        streams = self._load_streams_from_config(cfg_path)
        if not streams:
            print("[TrroFieldVR] WARN: no valid 'outside' streams in config.json; NOTHING will be sent for video.")
            return

        for sc in streams:
            sender = _CameraSender(
                dll=self._dll,
                stream_id=sc["stream_id"],
                url=sc["url"],
                width=sc["width"],
                height=sc["height"],
                fps=sc["fps"],
                stop_evt = self._stop_evt
            )
            sender.start()
            self._camera_threads.append(sender)

        print(f"[TrroFieldVR] started {len(self._camera_threads)} video stream(s) from config.json.")

    # ---- 工具 ----
    @staticmethod
    def _ms_now():
        return int(time.time() * 1000)

    def _pack_frame(self, payload: bytes, mtype=MSG_DATA, seq=None) -> bytes:
        if len(payload) > MAX_PAYLOAD:
            raise ValueError(f"payload too large ({len(payload)}) > {MAX_PAYLOAD}; consider fragmentation")
        seq = (seq if seq is not None else self._seq) & 0xFFFFFFFF or 1
        hdr = struct.pack(HDR_FMT, MAGIC, PROTO_VER, ROLE_FIELD, int(mtype), 0, seq, self._ms_now(), len(payload))
        frame = hdr + payload 
        # 自增序号
        if seq == self._seq:
            self._seq = (self._seq + 1) & 0xFFFFFFFF or 1
        return frame

    def _resolve_path(self, p: str) -> str:
        if os.path.isabs(p):
            return p
        here = os.path.dirname(os.path.abspath(__file__))
        c1 = os.path.normpath(os.path.join(here, p))
        if os.path.exists(c1):
            return c1
        c2 = os.path.normpath(os.path.join(os.getcwd(), p))
        return c2

    @staticmethod
    def _load_streams_from_config(cfg_path: str):
        """
        读取 config.json，抽取 protocol == 'outside' 的条目：
            - 如果 url 缺省，优先 camera 索引 → /dev/video{camera}，否则 /dev/video0
        """
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[TrroFieldVR] load config.json failed: {e}")
            return []

        streams_cfg = cfg.get("streams_config", [])
        result = []
        for i, s in enumerate(streams_cfg):
            proto = s.get("protocol")
            if isinstance(proto, str) and proto.lower() != "outside":
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
