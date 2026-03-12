import json
from channels.generic.websocket import AsyncWebsocketConsumer


class BillingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer cho trang /billing.

    Lắng nghe group "billing_updates".
    Django Channels ánh xạ message type → method bằng cách thay '.' thành '_':
      - "billing.invoice_updated"  →  billing_invoice_updated()
      - "billing.payment_done"     →  billing_payment_done()
    """

    async def connect(self):
        self.group_name = "billing_updates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ------------------------------------------------------------------
    # Handlers — tên phải khớp: message type "a.b" → method "a_b"
    # ------------------------------------------------------------------

    async def billing_invoice_updated(self, event):
        """
        Nhận khi Clinical gửi chỉ lệnh CLS / kê đơn thuốc → hóa đơn được cập nhật.
        type: "billing.invoice_updated"
        """
        await self.send(text_data=json.dumps({
            'type': 'invoice_updated',
            'action': event.get('action', 'updated'),
            'invoice_id': event.get('invoice_id'),
        }))

    async def billing_payment_done(self, event):
        """
        Nhận khi thu ngân hoàn tất thanh toán → báo các trang khác (RIS/LIS/Pharmacy).
        type: "billing.payment_done"
        """
        await self.send(text_data=json.dumps({
            'type': 'payment_done',
            'invoice_id': event.get('invoice_id'),
            'visit_id': event.get('visit_id'),
        }))
