"""
MQTT状态同步运行脚本
用于启动MQTT状态同步服务，将MQTT中的状态信息同步到数据库中
"""

import sys
import os
import time
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components.MQTTStatusSync import MQTTStatusSync

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    主函数
    """
    global sync_service
    
    # 创建MQTT状态同步实例
    # 可以根据需要修改MQTT服务器地址和端口
    sync_service = MQTTStatusSync(
        db_path="EasyTeleop.db",
        mqtt_broker="121.43.162.224",  # 修改为实际的MQTT服务器地址
        mqtt_port=1883
    )
    
    try:
        # 启动同步服务
        sync_service.start_sync()
        logger.info("MQTT状态同步服务已启动，按 Ctrl+C 停止服务")
        
        # 保持程序运行
        while True:
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"MQTT状态同步服务运行出错: {str(e)}")
        sync_service.stop_sync()
        sys.exit(1)

if __name__ == "__main__":
    main()