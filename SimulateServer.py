import socket
import threading
import time
import math

class SimulatorServer:
    def __init__(self, host='0.0.0.0', port=12345, update_interval=0.05):
        """
        初始化位姿模拟器服务器
        :param host: 服务器绑定的IP地址
        :param port: 服务器监听的端口
        :param update_interval: 位姿更新间隔（秒）
        """
        self.host = host
        self.port = port
        self.update_interval = update_interval
        self.running = False
        self.server_socket = None
        self.client_connections = []
        self.client_lock = threading.Lock()
        
        # 圆形轨迹参数
        self.radius = 0.1  # 圆的半径（米）
        self.center_x = 0.5  # 圆心X坐标
        self.center_y = 0.3  # 圆心Y坐标
        self.z_height = 0.4  # Z轴高度
        self.angle = 0  # 当前角度
        self.angular_velocity = math.pi  # 角速度（弧度/秒）- 约30秒一圈
        
        # 姿态参数（固定）
        self.roll = 0.0
        self.pitch = math.pi
        self.yaw = 0.0

    def generate_circle_pose(self):
        """生成圆形轨迹上的位姿数据"""
        # 计算当前角度的X和Y坐标
        x = self.center_x + self.radius * math.cos(self.angle)
        y = self.center_y + self.radius * math.sin(self.angle)
        z = self.z_height
        
        # 更新角度（确保在0到2π之间）
        self.angle = (self.angle + self.angular_velocity * self.update_interval) % (2 * math.pi)
        
        # 返回6D位姿数据 [x, y, z, roll, pitch, yaw]
        return [
            round(x, 4),
            round(y, 4),
            round(z, 4),
            round(self.roll, 4),
            round(self.pitch, 4),
            round(self.yaw, 4)
        ]

    def handle_client(self, client_socket):
        """处理客户端连接，发送位姿数据"""
        print(f"New client connected")
        try:
            while self.running:
                # 生成位姿数据
                pose = self.generate_circle_pose()
                
                # 转换为字符串格式发送（例如："0.5,0.3,0.4,0.0,3.14,0.0"）
                pose_str = ",".join(map(str, pose)) + "\n"
                client_socket.sendall(pose_str.encode('utf-8'))
                
                # 等待下一次更新
                time.sleep(self.update_interval)
        except (ConnectionResetError, BrokenPipeError):
            print("Client disconnected")
        finally:
            with self.client_lock:
                if client_socket in self.client_connections:
                    self.client_connections.remove(client_socket)
            client_socket.close()

    def start(self):
        """启动服务器"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Pose simulator server started on {self.host}:{self.port}")
        print(f"Generating circular path with radius {self.radius}m")
        
        # 启动接受客户端连接的线程
        accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
        accept_thread.start()
        
        try:
            # 保持服务器运行
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Server is shutting down...")
            self.stop()

    def accept_connections(self):
        """接受客户端连接的线程"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                with self.client_lock:
                    self.client_connections.append(client_socket)
                # 为每个客户端启动一个处理线程
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True)
                client_thread.start()
            except OSError:
                # 服务器关闭时会抛出此异常
                break

    def stop(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # 关闭所有客户端连接
        with self.client_lock:
            for client_socket in self.client_connections:
                try:
                    client_socket.close()
                except:
                    pass
        print("Server stopped")

if __name__ == "__main__":
    # 创建并启动服务器
    server = SimulatorServer(host='0.0.0.0', port=12345, update_interval=0.05)
    server.start()
    