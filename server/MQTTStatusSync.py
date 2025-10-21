import paho.mqtt.client as mqtt
import sqlite3
import json
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MQTTStatusSync:
    """
    MQTT状态同步模块
    负责从MQTT订阅状态更新消息，并将状态同步到数据库中
    """
    
    def __init__(self, db_path: str = "EasyTeleop.db", mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        self.db_path = db_path
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_client: Optional[mqtt.Client] = None
        
    def setup_mqtt(self):
        """
        设置MQTT客户端并连接到MQTT服务器
        """
        try:
            # 使用 MQTT v3.1.1 协议和回调 API v2
            self.mqtt_client = mqtt.Client(
                protocol=mqtt.MQTTv311, 
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
            
            # 设置回调函数
            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_message = self._on_message
            self.mqtt_client.on_disconnect = self._on_disconnect
            
            # 连接到MQTT服务器
            logger.info(f"正在连接MQTT服务器 {self.mqtt_broker}:{self.mqtt_port}...")
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            
        except Exception as e:
            logger.error(f"MQTT服务器连接失败: {str(e)}")
            raise
            
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """
        MQTT连接回调函数
        """
        if rc == 0:
            logger.info("MQTT连接成功")
            # 订阅所有相关主题
            client.subscribe("node/+/status")
            client.subscribe("node/+/device/+/status")
            client.subscribe("node/+/teleop-group/+/status")
            client.subscribe("node/+/teleop-group/+/collecting")
            logger.info("已订阅所有状态主题")
        else:
            logger.error(f"MQTT连接失败，错误代码: {rc}")
            
    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        """
        MQTT断开连接回调函数
        """
        logger.warning(f"MQTT连接断开，错误代码: {reason_code}")
            
    def _on_message(self, client, userdata, msg):
        """
        MQTT消息接收回调函数
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.debug(f"收到MQTT消息 - 主题: {topic}, 内容: {payload}")
            
            # 解析主题并更新数据库
            self._process_message(topic, payload)
            
        except Exception as e:
            logger.error(f"处理MQTT消息时出错: {str(e)}")
            
    def _process_message(self, topic: str, payload: str):
        """
        处理MQTT消息并更新数据库
        """
        # 解析主题
        # 格式: node/{node_id}/[status|device/{device_id}/status|teleop-group/{group_id}/status|teleop-group/{group_id}/collecting]
        topic_parts = topic.split('/')
        
        if len(topic_parts) < 3:
            logger.warning(f"无效的主题格式: {topic}")
            return
            
        node_id = topic_parts[1]
        
        # 确保node_id是数字
        try:
            node_id = int(node_id)
        except ValueError:
            logger.warning(f"无效的节点ID: {node_id}")
            return
            
        if len(topic_parts) == 3 and topic_parts[2] == 'status':
            # 节点状态更新
            self._update_node_status(node_id, payload)
        elif len(topic_parts) == 5 and topic_parts[2] == 'device' and topic_parts[4] == 'status':
            # 设备状态更新
            device_id = topic_parts[3]
            try:
                device_id = int(device_id)
                self._update_device_status(node_id, device_id, payload)
            except ValueError:
                logger.warning(f"无效的设备ID: {device_id}")
        elif len(topic_parts) == 5 and topic_parts[2] == 'teleop-group' and topic_parts[4] in ['status', 'collecting']:
            # 遥操组状态更新
            group_id = topic_parts[3]
            status_type = topic_parts[4]  # 'status' or 'collecting'
            try:
                group_id = int(group_id)
                if status_type == 'status':
                    self._update_teleop_group_status(node_id, group_id, payload)
                elif status_type == 'collecting':
                    self._update_teleop_group_collecting_status(node_id, group_id, payload)
            except ValueError:
                logger.warning(f"无效的遥操组ID: {group_id}")
        else:
            logger.warning(f"未识别的主题格式: {topic}")
            
    @contextmanager
    def _get_db_connection(self):
        """
        数据库连接上下文管理器
        """
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
            
    def _update_node_status(self, node_id: int, status: str):
        """
        更新节点状态到数据库
        """
        try:
            status_value = int(status)
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE nodes SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status_value, node_id)
                )
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"节点 {node_id} 状态已更新为 {status_value}")
                else:
                    logger.warning(f"未找到节点 {node_id}，无法更新状态")
        except Exception as e:
            logger.error(f"更新节点 {node_id} 状态时出错: {str(e)}")
            
    def _update_device_status(self, node_id: int, device_id: int, status: str):
        """
        更新设备状态到数据库
        """
        try:
            status_value = int(status)
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE devices SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND node_id = ?",
                    (status_value, device_id, node_id)
                )
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"设备 {device_id} 状态已更新为 {status_value}")
                else:
                    logger.warning(f"未找到设备 {device_id} (节点 {node_id})，无法更新状态")
        except Exception as e:
            logger.error(f"更新设备 {device_id} 状态时出错: {str(e)}")
            
    def _update_teleop_group_status(self, node_id: int, group_id: int, status: str):
        """
        更新遥操组状态到数据库
        """
        try:
            status_value = int(status)
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE teleop_groups SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND node_id = ?",
                    (status_value, group_id, node_id)
                )
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"遥操组 {group_id} 状态已更新为 {status_value}")
                else:
                    logger.warning(f"未找到遥操组 {group_id} (节点 {node_id})，无法更新状态")
        except Exception as e:
            logger.error(f"更新遥操组 {group_id} 状态时出错: {str(e)}")
            
    def _update_teleop_group_collecting_status(self, node_id: int, group_id: int, status: str):
        """
        更新遥操组采集状态到数据库
        """
        try:
            status_value = int(status)
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE teleop_groups SET capture_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND node_id = ?",
                    (status_value, group_id, node_id)
                )
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"遥操组 {group_id} 采集状态已更新为 {status_value}")
                else:
                    logger.warning(f"未找到遥操组 {group_id} (节点 {node_id})，无法更新采集状态")
        except Exception as e:
            logger.error(f"更新遥操组 {group_id} 采集状态时出错: {str(e)}")
            
    def start_sync(self):
        """
        开始同步状态
        """
        if not self.mqtt_client:
            self.setup_mqtt()
            
        logger.info("开始MQTT状态同步...")
        self.mqtt_client.loop_start()
        
    def stop_sync(self):
        """
        停止同步状态
        """
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT状态同步已停止")