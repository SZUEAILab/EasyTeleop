import socket
import json
import threading
class VRSocket:
    def __init__(self, config):
        # 初始化 socket 连接
        self.ip = config["ip"]
        self.port = config.get("port", 12345)

        self._on_message = self._default_callback
        self._on_disconnect = self._default_callback
        self._on_connect = self._default_callback

        self.sock = None
        self.connect()

    def _default_callback(self):
        pass
    
    def on_message(self,callback):
        self._on_message = callback
        
    def on_disconnect(self,callback):
        self._on_disconnect = callback
        
    def on_connect(self,callback):
        self._on_connect = callback
        
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.ip, self.port))
        print(f"已连接到 Unity 服务器 {self.ip}:{self.port}", True)
        
    def socket_receiver(self):
        """
        Socket 接收线程
        """
        buffer = ""
        while True:
            try:
                data = self.sock.recv(1024)
                if not data:
                    print("[Quest断开连接]")
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip() == "":
                        continue
                    try:
                        msg = json.loads(line)
                        self._on_message(msg)
                    except json.JSONDecodeError as e:
                        print("[JSON解析失败]", e)
                        break
            except Exception as e:
                print(f"Socket接收异常: {e}", True)
                break

    def start(self):
        """
        以非阻塞方式启动 socket_receiver 线程
        """
        receiver_thread = threading.Thread(target=self.socket_receiver, daemon=True)
        receiver_thread.start()