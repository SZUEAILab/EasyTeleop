import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components.WebSocketRPC import WebSocketRPC


async def run_server():
    """运行RPC服务器测试"""
    print("启动RPC服务器...")
    
    # 创建RPC服务器实例
    server = WebSocketRPC()
    
    # 注册服务器方法
    @server.register_method('add')
    async def add(a: int, b: int) -> int:
        print(f"服务器: 计算 {a} + {b}")
        return a + b
    
    @server.register_method('get_server_info')
    async def get_server_info() -> dict:
        print("服务器: 提供服务器信息")
        return {
            'name': 'WebSocket RPC Server',
            'version': '1.0'
        }
    
    # 启动后主动调用客户端方法
    async def server_calls():
        # 等待连接建立
        while not server.websocket or server.websocket.state.name == 'CLOSED':
            await asyncio.sleep(0.1)
        
        try:
            # 调用客户端方法
            print("\n服务器: 调用客户端的 multiply 方法")
            result = await server.call('multiply', [3, 4])
            print(f"服务器: 客户端返回结果: {result}")
            
            # 发送通知
            print("\n服务器: 向客户端发送问候通知")
            await server.notify('greet', {'message': 'Hello from server!'})
        except Exception as e:
            print(f"服务器调用出错: {e}")
    
    # 启动服务器和服务器端调用任务
    print("服务器已启动，等待客户端连接...")
    await asyncio.gather(
        server.serve('localhost', 8765),
        server_calls()
    )


async def run_client():
    """运行RPC客户端测试"""
    print("启动RPC客户端...")
    
    # 创建RPC客户端实例
    client = WebSocketRPC()
    
    # 注册客户端方法
    @client.register_method('multiply')
    async def multiply(a: int, b: int) -> int:
        print(f"客户端: 计算 {a} * {b}")
        return a * b
    
    @client.register_method('greet')
    async def greet(params: dict):
        message = params.get('message', '')
        print(f"客户端: 收到问候 - {message}")
        return {"received": True, "message": message}
    
    # 连接服务器后主动调用服务器方法
    async def client_calls():
        # 等待连接建立
        while not client.websocket or client.websocket.state.name == 'CLOSED':
            await asyncio.sleep(0.1)
        
        try:
            # 调用服务器方法
            print("\n客户端: 调用服务器的 add 方法")
            result = await client.call('add', [5, 7])
            print(f"客户端: 服务器返回结果: {result}")
            
            print("\n客户端: 调用服务器的 get_server_info 方法")
            info = await client.call('get_server_info')
            print(f"客户端: 服务器信息: {info}")
        except Exception as e:
            print(f"客户端调用出错: {e}")
    
    # 连接到服务器并启动客户端调用任务
    print("客户端正在连接服务器...")
    await asyncio.gather(
        client.connect('ws://localhost:8765'),
        client_calls()
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "server":
            asyncio.run(run_server())
        elif sys.argv[1] == "client":
            asyncio.run(run_client())
    else:
        print("使用方法:")
        print("  python rpc_test.py server  - 启动服务器")
        print("  python rpc_test.py client  - 启动客户端")