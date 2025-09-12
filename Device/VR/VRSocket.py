import socket
import json
import threading
from ..BaseDevice import BaseDevice


class VRSocket(BaseDevice):
    # 定义需要的配置字段为静态字段
    need_config = {
        "ip": "服务器IP地址",
        "port": "服务器端口号"
    }
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # 初始化 socket 连接相关变量
        self.ip = None
        self.port = None
        self.sock = None
        self.receiver_thread = None
        
        # 设置事件回调
        self._events = {
             "message": self._default_callback,
        }
        
        # 如果提供了配置，则设置配置
        if config:
            self.set_config(config)

    def set_config(self, config):
        """
        设置设备配置，验证配置是否符合need_config要求
        :param config: 配置字典
        :return: 是否设置成功
        """
        # 检查必需的配置字段
        for key in self.need_config:
            if key not in config:
                raise ValueError(f"缺少必需的配置字段: {key}")
        
        self.config = config
        self.ip = config["ip"]
        self.port = int(config["port"])
        
        return True

    def connect(self):
        """
        建立到VR设备的Socket连接
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.ip, self.port))
            self.set_conn_status(1)
            self.emit("connect", f"已连接到 Unity 服务器 {self.ip}:{self.port}")
        except Exception as e:
            self.set_conn_status(2)
            self.emit("error_occurred", f"连接失败: {e}")

    def socket_receiver(self):
        """
        Socket 接收线程
        """
        buffer = ""
        while True:
            try:
                # 检查socket是否仍然连接
                if self.sock is None or self.get_conn_status() != 1:
                    break
                    
                data = self.sock.recv(1024)
                if not data:
                    self.emit("disconnect", "[Quest断开连接]")
                    self.set_conn_status(2)
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip() == "":
                        continue
                    try:
                        msg = json.loads(line)
                        self.emit("message", msg)
                    except json.JSONDecodeError as e:
                        self.emit("error_occurred", f"[JSON解析失败]: {e}")
                        break
            except Exception as e:
                if self.get_conn_status() == 1:  # 只有在连接状态时才报告异常
                    self.emit("error_occurred", f"Socket接收异常: {e}")
                    self.set_conn_status(2)
                break

    def start(self):
        """
        启动设备
        :return: 是否启动成功
        """
        try:
            self.connect()
            if self.receiver_thread is None or not self.receiver_thread.is_alive():
                self.receiver_thread = threading.Thread(target=self.socket_receiver, daemon=True)
            if self.get_conn_status() == 1:  # 只有连接成功才启动线程
                self.receiver_thread.start()
                return True
            return False
        except Exception as e:
            self.emit("error_occurred", f"启动失败: {e}")
            return False

    def stop(self):
        """
        停止设备
        :return: 是否停止成功
        """
        try:
            if self.sock:
                self.sock.close()
                self.sock = None
                
            self.set_conn_status(0)  # 设置为未连接状态
            return True
        except Exception as e:
            self.emit("error_occurred", f"停止设备时出错: {e}")
            return False