"""
QMS WebSocket Consumer
Broadcasts real-time queue board updates to display screens.

Protocol:
- Client connects to: ws://host/ws/qms/display/<station_id>/
- Server pushes: { "type": "queue_update", "data": { ...queue board... } }
- Client can send: { "type": "ping" } for keepalive
"""

import json
import logging

try:
    from channels.generic.websocket import AsyncWebsocketConsumer
except ImportError:
    from channels.generic.websocket import AsyncWebSocketConsumer as AsyncWebsocketConsumer

from channels.db import database_sync_to_async
from .models import ServiceStation
from .services import ClinicalQueueService

logger = logging.getLogger(__name__)


class QueueDisplayConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for QMS display screens.

    Each display connects with a station_id and joins the group
    'qms_station_{station_id}'. When queue changes occur,
    the full board is broadcast to all displays for that station.
    """

    def get_group_name(self):
        return f"qms_station_{self.station_id}"

    async def connect(self):
        self.station_id = self.scope['url_route']['kwargs']['station_id']
        self.group_name = self.get_group_name()

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )
        await self.accept()

        # Send initial queue board on connect
        board_data = await self._get_board()
        await self.send(text_data=json.dumps({
            'type': 'queue_update',
            'data': board_data,
        }))

        logger.info(f"Display connected: station={self.station_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )
        logger.info(f"Display disconnected: station={self.station_id}")

    async def receive(self, text_data):
        """Handle ping/pong keepalive from client."""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except (json.JSONDecodeError, Exception):
            pass

    # ── Group event handlers ────────────────────────────────────────

    async def queue_update(self, event):
        """Broadcast queue board update to connected display."""
        await self.send(text_data=json.dumps({
            'type': 'queue_update',
            'data': event['data'],
        }))

    # ── Helpers ──────────────────────────────────────────────────────

    @database_sync_to_async
    def _get_board(self):
        station = ServiceStation.objects.get(id=self.station_id)
        return ClinicalQueueService.get_queue_board(station)
