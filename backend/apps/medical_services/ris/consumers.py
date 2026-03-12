import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class RISConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer cho RIS — thông báo realtime về trạng thái ca chụp CĐHA.
    Group: ris_updates
    """

    async def connect(self):
        try:
            self.group_name = "ris_updates"

            if self.channel_layer is None:
                logger.error("RISConsumer: channel_layer is None — kiểm tra CHANNEL_LAYERS và Redis")
                await self.close(code=4500)
                return

            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            logger.info(f"RISConsumer: Client kết nối thành công vào nhóm '{self.group_name}'")
        except Exception as e:
            logger.error(f"RISConsumer: Lỗi khi kết nối WebSocket: {e}", exc_info=True)
            await self.close(code=4500)

    async def disconnect(self, close_code):
        try:
            if self.channel_layer is not None:
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
        except Exception as e:
            logger.warning(f"RISConsumer: Lỗi khi ngắt kết nối: {e}")
        logger.info(f"RISConsumer: Client ngắt kết nối (code={close_code})")

    # ------------------------------------------------------------------
    # Handler: Order created/updated (from post_save signal)
    # ------------------------------------------------------------------
    async def ris_order_updated(self, event):
        """Forward ris.order_updated event đến WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'ris_order_updated',
            'action': event.get('action', 'updated'),
            'order_id': event['order_id'],
            'status': event['status'],
        }))

    # ------------------------------------------------------------------
    # Handler: New DICOM study received from Orthanc (from Celery task)
    # ------------------------------------------------------------------
    async def ris_new_study(self, event):
        """Forward ris.new_study event đến WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'ris_new_study',
            'order_id': event['order_id'],
            'study_uid': event['study_uid'],
            'accession_number': event.get('accession_number', ''),
            'patient_name': event.get('patient_name', ''),
            'study_description': event.get('study_description', ''),
        }))
