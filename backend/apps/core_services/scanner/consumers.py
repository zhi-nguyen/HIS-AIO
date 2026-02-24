"""
Scanner WebSocket Consumer
Handles station pairing between PC workstation and mobile phone scanner.

Protocol:
- Both PC and Phone connect to: ws://host/ws/scanner/<station_id>/
- Phone sends: { "type": "scan", "content": "<raw_scanned_string>" }
- PC receives: { "type": "scan_event", "content": "<raw_scanned_string>", "timestamp": "..." }
- PC sends back: { "type": "ack" } → Phone knows PC received it (vibration trigger)
"""

import json
from datetime import datetime
try:
    from channels.generic.websocket import AsyncWebsocketConsumer
except ImportError:
    from channels.generic.websocket import AsyncWebSocketConsumer as AsyncWebsocketConsumer


class ScannerConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for remote scanner station pairing.
    
    All clients connected to the same station_id share a channel group.
    When a phone scans data, it broadcasts to the group.
    The PC client(s) in the group receive the scan event.
    """

    async def connect(self):
        self.station_id = self.scope['url_route']['kwargs']['station_id']
        self.group_name = f'scanner_{self.station_id}'

        # Join the station's channel group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'station_id': self.station_id,
            'message': f'Connected to station {self.station_id}',
        }))

    async def disconnect(self, close_code):
        # Leave the station's channel group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handle incoming messages.
        - Phone sends scan data → broadcast to group
        - PC sends ack → broadcast to group (for vibration feedback)
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON',
            }))
            return

        msg_type = data.get('type', '')

        if msg_type == 'scan':
            # Phone scanned something → broadcast to all in group (PC will pick it up)
            content = data.get('content', '')
            if not content:
                return

            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'scan_event',
                    'content': content,
                    'timestamp': datetime.now().isoformat(),
                    'sender_channel': self.channel_name,
                }
            )

        elif msg_type == 'ack':
            # PC acknowledges receipt → broadcast to group (Phone will vibrate)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'ack_event',
                    'sender_channel': self.channel_name,
                }
            )

    async def scan_event(self, event):
        """
        Receive scan_event from group broadcast.
        Skip sending back to the original sender (Phone doesn't need its own scan back).
        """
        if event.get('sender_channel') == self.channel_name:
            return  # Don't echo back to sender

        await self.send(text_data=json.dumps({
            'type': 'scan_event',
            'content': event['content'],
            'timestamp': event['timestamp'],
        }))

    async def ack_event(self, event):
        """
        Receive ack_event from group broadcast.
        Skip sending back to the original sender (PC doesn't need its own ack).
        """
        if event.get('sender_channel') == self.channel_name:
            return  # Don't echo back to sender

        await self.send(text_data=json.dumps({
            'type': 'ack',
        }))
