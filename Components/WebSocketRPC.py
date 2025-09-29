import json
import asyncio
import websockets
import logging
from uuid import uuid4
from typing import Dict, Callable, Awaitable, Any, Optional
from websockets.server import WebSocketServerProtocol


class WebSocketRPC:
    """
    基于WebSocket的双向JSON-RPC实现
    支持双方同时作为客户端和服务器发起RPC调用
    """

    def __init__(self):
        # 注册的方法映射
        self.methods: Dict[str, Callable[..., Awaitable[Any]]] = {}
        # 等待响应的回调函数，key为请求ID
        self.pending_responses: Dict[str, asyncio.Future] = {}
        # WebSocket连接对象
        self.websocket: Optional[WebSocketServerProtocol] = None
        # 请求ID计数器
        self.request_id_counter = 0
        # 日志记录器
        self.logger = logging.getLogger(__name__)

    def register_method(self, name: str, method: Callable[..., Awaitable[Any]] = None):
        """
        注册可被远程调用的方法
        :param name: 方法名称
        :param method: 实际执行函数
        """
        if method is not None:
            self.methods[name] = method
        else:
            # 作为装饰器使用
            def decorator(func):
                self.methods[name] = func
                return func
            return decorator

    async def call(self, method: str, params: Any = None, is_notification: bool = False) -> Any:
        """
        调用远程方法
        :param method: 方法名称
        :param params: 方法参数
        :param is_notification: 是否为通知（不需要响应）
        :return: 远程方法返回结果
        """
        if not self.websocket or self.websocket.state.name == 'CLOSED':
            raise Exception("WebSocket连接未建立或已关闭")

        # 构造请求
        request = {
            "jsonrpc": "2.0",
            "method": method,
        }

        if params is not None:
            request["params"] = params

        # 记录发送的请求
        self.logger.info(f"发送RPC请求: {request}")

        # 如果是通知，不设置ID，也不等待响应
        if not is_notification:
            self.request_id_counter += 1
            request_id = self.request_id_counter
            request["id"] = request_id

            # 创建Future对象等待响应
            future = asyncio.Future()
            self.pending_responses[request_id] = future

        # 发送请求
        await self.websocket.send(json.dumps(request))

        # 如果是通知，直接返回
        if is_notification:
            return None

        # 等待响应
        try:
            return await asyncio.wait_for(future, timeout=30.0)  # 30秒超时
        except asyncio.TimeoutError:
            raise Exception(f"调用方法 {method} 超时")

    async def notify(self, method: str, params: Any = None):
        """
        发送通知（不需要响应的请求）
        :param method: 方法名称
        :param params: 方法参数
        """
        await self.call(method, params, is_notification=True)

    async def _handle_request(self, request: dict):
        """处理收到的RPC请求"""
        request_id = request.get('id')
        method_name = request.get('method')
        params = request.get('params', [])

        # 记录收到的请求
        self.logger.info(f"收到RPC请求: {request}")

        # 构建响应基础结构
        response = {
            'jsonrpc': '2.0',
        }

        # 如果有ID，需要返回响应
        if request_id is not None:
            response['id'] = request_id

        try:
            # 检查方法是否存在
            if method_name not in self.methods:
                raise ValueError(f"Method {method_name} not found")

            # 调用方法
            method = self.methods[method_name]

            # 处理不同类型的参数
            # if isinstance(params, list):
            #     result = await method(*params)
            # elif isinstance(params, dict):
            #     result = await method(**params)
            # else:
            #     result = await method(params)

            result = await method(params)

            # 成功响应
            if request_id is not None:
                response['result'] = result

        except Exception as e:
            # 错误响应
            if request_id is not None:
                response['error'] = {
                    'code': -32603,
                    'message': str(e),
                    'data': type(e).__name__
                }

        # 记录发送的响应
        self.logger.info(f"发送RPC响应: {response}")

        # 发送响应（仅当有ID且连接存在时）
        if request_id is not None and self.websocket and self.websocket.state.name != 'CLOSED':
            await self.websocket.send(json.dumps(response))

    def _handle_response(self, response: dict):
        """处理收到的RPC响应"""
        response_id = response.get('id')
        
        # 记录收到的响应
        self.logger.info(f"收到RPC响应: {response}")

        if response_id in self.pending_responses:
            future = self.pending_responses.pop(response_id)

            # 处理错误响应
            if 'error' in response:
                future.set_exception(Exception(
                    f"RPC Error {response['error']['code']}: {response['error']['message']}"
                ))
            # 处理成功响应
            else:
                future.set_result(response.get('result'))

    async def _process_single_message(self, data: dict):
        """处理单个消息"""
        # 判断是请求还是响应
        if 'method' in data:
            await self._handle_request(data)
        elif 'id' in data:
            self._handle_response(data)

    async def _message_handler(self, websocket: WebSocketServerProtocol):
        """消息处理主循环"""
        self.websocket = websocket

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)

                    # 批量请求/响应
                    if isinstance(data, list):
                        for item in data:
                            await self._process_single_message(item)
                    # 单个请求/响应
                    else:
                        await self._process_single_message(data)

                except json.JSONDecodeError:
                    if websocket.state.name != 'CLOSED':
                        await websocket.send(json.dumps({
                            'jsonrpc': '2.0',
                            'id': None,
                            'error': {'code': -32700, 'message': 'Parse error'}
                        }))
                except Exception as e:
                    if websocket.state.name != 'CLOSED':
                        await websocket.send(json.dumps({
                            'jsonrpc': '2.0',
                            'id': None,
                            'error': {'code': -32603, 'message': f'Internal error: {str(e)}'}
                        }))

        finally:
            self.websocket = None
            # 清除所有未完成的请求
            for future in self.pending_responses.values():
                if not future.done():
                    future.set_exception(ConnectionAbortedError("WebSocket connection closed"))
            self.pending_responses.clear()

    async def serve(self, host: str = "localhost", port: int = 8765):
        """
        启动WebSocket服务器
        :param host: 监听地址
        :param port: 监听端口
        """
        async with websockets.serve(self._message_handler, host, port):
            await asyncio.Future()  # 运行直到被中断

    async def connect(self, uri: str):
        """
        连接到WebSocket服务器
        :param uri: WebSocket服务器地址
        """
        websocket = await websockets.connect(uri)
        await self._message_handler(websocket)