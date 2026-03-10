import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class LISConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.group_name = "lis_updates"

            # Kiểm tra channel_layer có sẵn không (Redis phải đang chạy)
            if self.channel_layer is None:
                logger.error("LISConsumer: channel_layer is None — kiểm tra cấu hình CHANNEL_LAYERS và Redis")
                await self.close(code=4500)
                return

            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            logger.info(f"LISConsumer: Client kết nối thành công vào nhóm '{self.group_name}'")
        except Exception as e:
            logger.error(f"LISConsumer: Lỗi khi kết nối WebSocket: {e}", exc_info=True)
            await self.close(code=4500)

    async def disconnect(self, close_code):
        try:
            if self.channel_layer is not None:
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
        except Exception as e:
            logger.warning(f"LISConsumer: Lỗi khi ngắt kết nối: {e}")
        logger.info(f"LISConsumer: Client ngắt kết nối khỏi '{self.group_name}' (code={close_code})")

    # Receive message from room group
    async def lis_order_updated(self, event):
        order_id = event['order_id']
        status = event['status']
        action = event.get('action', 'updated')

        logger.info(f"LISConsumer: Forwarding lis_order_updated event to WS client for order {order_id} (action: {action})")

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'lis_order_updated',
            'action': action,
            'order_id': order_id,
            'status': status
        }))

