from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from .models import ClinicalRecord
from .serializers import ClinicalRecordSerializer

class ClinicalRecordViewSet(viewsets.ModelViewSet):
    queryset = ClinicalRecord.objects.all().order_by('-created_at')
    serializer_class = ClinicalRecordSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['visit__visit_code', 'visit__patient__patient_code']
    filterset_fields = ['doctor', 'is_finalized']

    def perform_create(self, serializer):
        # Gắn bác sĩ đang đăng nhập nếu có staff_profile
        user = self.request.user
        if hasattr(user, 'staff_profile') and user.staff_profile:
            serializer.save(doctor=user.staff_profile)
        else:
            serializer.save()

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """
        POST /api/v1/emr/records/{id}/finalize/

        Hoàn tất khám:
        1. Khóa hồ sơ bệnh án (is_finalized = True)
        2. Cập nhật trạng thái lượt khám → PENDING_PAYMENT
        3. Sync đơn thuốc vào hóa đơn (nếu có)
        4. Broadcast WS cho /billing realtime
        """
        record = self.get_object()
        if record.is_finalized:
            return Response({'error': 'Hồ sơ đã được hoàn tất.'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.core_services.reception.models import Visit
        from apps.core_services.billing.services import BillingService
        import logging
        logger = logging.getLogger(__name__)

        with transaction.atomic():
            # 1. Lock clinical record
            record.is_finalized = True
            record.save(update_fields=['is_finalized'])

            # 2. Move visit to billing queue
            visit = record.visit
            visit.status = Visit.Status.PENDING_PAYMENT
            visit.save(update_fields=['status'])

        # 3. Sync all active prescriptions to billing invoice (outside atomic to allow WS)
        from apps.medical_services.pharmacy.models import Prescription
        active_prescriptions = Prescription.objects.filter(
            visit=visit
        ).exclude(status=Prescription.Status.CANCELLED)

        for rx in active_prescriptions:
            try:
                BillingService.finalize_prescription_to_invoice(rx)
            except Exception as e:
                logger.error(f"Failed to sync prescription {rx.pk} to billing on finalize: {e}")

        # 4. Broadcast billing WS so /billing page refreshes
        def _broadcast_billing_ws():
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        "billing_updates",
                        {
                            "type": "billing.invoice_updated",
                            "visit_id": str(visit.id),
                            "visit_code": visit.visit_code,
                            "action": "exam_finalized",
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to broadcast billing WS on finalize: {e}")

        transaction.on_commit(_broadcast_billing_ws)

        return Response({'status': 'finalized', 'visit_status': 'PENDING_PAYMENT'})

