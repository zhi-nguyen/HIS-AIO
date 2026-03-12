import json
from channels.generic.websocket import AsyncWebsocketConsumer


class PharmacistConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer cho trang /pharmacist.
    
    Nhận thông báo đơn thuốc mới cần cấp sau khi bệnh nhân thanh toán.
    """

    async def connect(self):
        self.group_name = "pharmacist_updates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Nhận message từ group và chuyển xuống WebSocket client
    async def pharmacist_prescription_ready(self, event):
        """Đơn thuốc đã thanh toán — sẵn sàng cấp phát."""
        await self.send(text_data=json.dumps({
            "type": "pharmacist.prescription_ready",
            "prescription_id": event.get("prescription_id"),
            "prescription_code": event.get("prescription_code"),
            "visit_code": event.get("visit_code"),
            "patient_name": event.get("patient_name"),
            "patient_dob": event.get("patient_dob"),
            "patient_gender": event.get("patient_gender"),
            "diagnosis": event.get("diagnosis"),
            "note": event.get("note"),
            "medications": event.get("medications", []),
            "total_price": event.get("total_price"),
            "timestamp": event.get("timestamp"),
        }))
