import numpy as np
import socket
import json
import time
from config import Quest_ip, Quest_port

def generate_box_point_cloud(center, size, num_points):
    """
    生成长方体点云
    :param center: (x, y, z) 长方体中心
    :param size: (dx, dy, dz) 长方体三边长
    :param num_points: 点云总数
    :return: (N, 3) 的numpy数组
    """
    cx, cy, cz = center
    dx, dy, dz = size

    # 在长方体范围内均匀采样
    xs = np.random.uniform(cx - dx/2, cx + dx/2, num_points)
    ys = np.random.uniform(cy - dy/2, cy + dy/2, num_points)
    zs = np.random.uniform(cz - dz/2, cz + dz/2, num_points)

    points = np.stack([xs, ys, zs], axis=1)
    return points

def send_point_cloud_json(points, host, port, sock=None):
    """
    以JSON格式发送点云数据到指定主机和端口
    :param points: (N, 3) 的numpy数组
    :param host: 目标主机地址
    :param port: 目标端口
    :param sock: 可选，已连接的socket对象
    """
    points_list = [{"x": float(x), "y": float(y), "z": float(z)} for x, y, z in points]
    data = {"points": points_list}
    json_str = json.dumps(data) + "\n"  # 以换行符结尾，便于接收端分包

    if sock is not None:
        sock.sendall(json_str.encode("utf-8"))
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(json_str.encode("utf-8"))

if __name__ == "__main__":
    center = (0.5, 0.5, 0.5)  # 长方体中心
    size = (0.5, 0.6, 0.3)    # 长1，宽2，高0.5
    num_points = 100

    # 持续不断发送点云
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((Quest_ip, 12346))
        while True:
            point_cloud = generate_box_point_cloud(center, size, num_points)
            send_point_cloud_json(point_cloud, host=None, port=None, sock=s)
            time.sleep(0.5)  # 每0.1秒发送一次，可根据需要调