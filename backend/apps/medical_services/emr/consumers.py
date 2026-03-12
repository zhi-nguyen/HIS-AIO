import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class ClinicalConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer cho Clinical (EMR) — nhận thông báo realtime về kết quả CLS (RIS/LIS).
    Group: clinical_visit_{visit_id}
    """

    async def connect(self):
        try:
            self.visit_id = self.scope['url_route']['kwargs']['visit_id']
            self.group_name = f"clinical_visit_{self.visit_id}"

            if self.channel_layer is None:
                logger.error("ClinicalConsumer: channel_layer is None")
                await self.close(code=4500)
                return

            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            logger.info(f"ClinicalConsumer: Client kết nối nhóm '{self.group_name}'")
        except Exception as e:
            logger.error(f"ClinicalConsumer: Lỗi khi kết nối WebSocket: {e}", exc_info=True)
            await self.close(code=4500)

    async def disconnect(self, close_code):
        try:
            if self.channel_layer is not None and hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
        except Exception as e:
            logger.warning(f"ClinicalConsumer: Lỗi khi ngắt kết nối: {e}")
        logger.info(f"ClinicalConsumer: Client ngắt kết nối (code={close_code})")

    async def clinical_cls_updated(self, event):
        """Forward cls_updated event đến WebSocket client."""
        data = {
            'type': 'cls_result_updated',
            'service_type': event.get('service_type', ''),
            'order_id': event.get('order_id', ''),
            'status': event.get('status', ''),
        }
        
        # Forward RIS fields
        if 'procedure_name' in event:
            data['procedure_name'] = event.get('procedure_name')
        if 'findings' in event:
            data['findings'] = event.get('findings')
        if 'conclusion' in event:
            data['conclusion'] = event.get('conclusion')
        if 'is_abnormal' in event:
            data['is_abnormal'] = event.get('is_abnormal')
            
        # Forward LIS fields
        if 'abnormal_items' in event:
            data['abnormal_items'] = event.get('abnormal_items')
            
        await self.send(text_data=json.dumps(data))
