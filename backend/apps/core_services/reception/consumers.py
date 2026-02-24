"""
Reception WebSocket Consumer
Broadcasts real-time notifications to Reception screens when new visits are created.

Protocol:
- Client connects to: ws://host/ws/reception/
- Server pushes: { "type": "new_visit", "visit": { ...visit data... } }
"""

import json
try:
    from channels.generic.websocket import AsyncWebsocketConsumer
except ImportError:
    from channels.generic.websocket import AsyncWebSocketConsumer as AsyncWebsocketConsumer


class ReceptionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time Reception notifications.

    All connected Reception clients join the 'reception_notifications' group.
    When a Visit is created (via signal), the group receives a broadcast.
    """

    GROUP_NAME = 'reception_notifications'

    async def connect(self):
        await self.channel_layer.group_add(
            self.GROUP_NAME,
            self.channel_name,
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to reception notifications',
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.GROUP_NAME,
            self.channel_name,
        )

    async def receive(self, text_data):
        # Reception clients are read-only — no incoming messages expected
        pass

    # ── Group event handlers ────────────────────────────────────────

    async def new_visit(self, event):
        """Broadcast new visit to connected clients."""
        await self.send(text_data=json.dumps({
            'type': 'new_visit',
            'visit': event['visit'],
        }))

    async def visit_updated(self, event):
        """Broadcast visit status update to connected clients."""
        await self.send(text_data=json.dumps({
            'type': 'visit_updated',
            'visit': event['visit'],
        }))
