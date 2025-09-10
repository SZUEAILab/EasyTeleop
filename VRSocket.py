import socket
import json
import threading
class VRSocket:
    def __init__(self, config):
        # 初始化 socket 连接
        self.ip = config["ip"]
        self.port = int(config["port"])
        
        self._events = {
             "message": self._default_callback,
             "disconnect": self._default_callback,
             "connect": self._default_callback,
        }

        # 连接状态: 0=未连接(灰色), 1=已连接(绿色), 2=断开连接(红色)
        self._conn_status = 0

        self.sock = None
    def get_conn_status(self):
        """
        获取设备连接状态
        :return: 0=未连接(灰色), 1=已连接(绿色), 2=断开连接(红色)
        """
        return self._conn_status

    def set_conn_status(self, status):
        """
        设置设备连接状态
        :param status: 0=未连接, 1=已连接, 2=断开连接
        """
        if status in (0, 1, 2):
            self._conn_status = status
            
    def on(self, event_name: str, callback):
        """注册事件回调函数"""
        # 如果事件不存在
        if event_name not in self._events:
            return
        # 将回调函数添加到事件列表中
        self._events[event_name] = callback

    def off(self, event_name: str):
        """移除事件回调函数"""
        if event_name not in self._events:
            return
        del self._events[event_name]

    def emit(self, event_name: str, *args, **kwargs):
        """触发事件，执行所有注册的回调函数"""
        if event_name not in self._events:
            return
        self._events[event_name](*args, **kwargs)

    def _default_callback(self,*args, **kwargs):
        pass
        
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.ip, self.port))
            self.set_conn_status(1)
            print(f"已连接到 Unity 服务器 {self.ip}:{self.port}", True)
        except Exception as e:
            self.set_conn_status(2)
            print(f"连接失败: {e}", True)
        
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
                    self.set_conn_status(2)
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip() == "":
                        continue
                    try:
                        msg = json.loads(line)
                        self.emit("message",msg)
                    except json.JSONDecodeError as e:
                        print("[JSON解析失败]", e)
                        break
            except Exception as e:
                print(f"Socket接收异常: {e}", True)
                self.set_conn_status(2)
                break

    def start(self):
        """
        以非阻塞方式启动 socket_receiver 线程
        """
        self.connect()

        receiver_thread = threading.Thread(target=self.socket_receiver, daemon=True)
        receiver_thread.start()