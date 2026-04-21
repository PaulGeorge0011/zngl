import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class MonitoringConsumer(AsyncWebsocketConsumer):
    """实时监控 WebSocket Consumer"""

    async def connect(self):
        await self.channel_layer.group_add('monitoring', self.channel_name)
        await self.accept()
        logger.info(f"WebSocket 连接: {self.channel_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('monitoring', self.channel_name)
        logger.info(f"WebSocket 断开: {self.channel_name}")

    async def alarm_triggered(self, event):
        """推送报警通知"""
        await self.send(text_data=json.dumps({
            'type': 'alarm',
            'data': event['data'],
        }, ensure_ascii=False))

    async def sensor_update(self, event):
        """推送传感器数据更新"""
        await self.send(text_data=json.dumps({
            'type': 'sensor',
            'data': event['data'],
        }, ensure_ascii=False))
