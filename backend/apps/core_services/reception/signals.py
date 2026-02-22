"""
Signals for Reception app.
Broadcasts WebSocket events when Visits are created.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Visit


@receiver(post_save, sender=Visit)
def broadcast_visit_event(sender, instance, created, **kwargs):
    """
    When a Visit is created, broadcast to the reception_notifications group
    so all connected Reception screens get a real-time update.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    # Build a lightweight payload (avoid heavy serialization)
    patient = instance.patient
    patient_name = getattr(patient, 'full_name', None)
    if not patient_name:
        patient_name = f"{patient.last_name} {patient.first_name}"

    visit_data = {
        'id': str(instance.id),
        'visit_code': instance.visit_code,
        'queue_number': instance.queue_number,
        'status': instance.status,
        'priority': instance.priority,
        'check_in_time': instance.check_in_time.isoformat() if instance.check_in_time else None,
        'chief_complaint': instance.chief_complaint or '',
        'patient': {
            'id': str(patient.id),
            'patient_code': patient.patient_code,
            'full_name': patient_name,
        },
    }

    event_type = 'new_visit' if created else 'visit_updated'

    async_to_sync(channel_layer.group_send)(
        'reception_notifications',
        {
            'type': event_type,
            'visit': visit_data,
        },
    )
