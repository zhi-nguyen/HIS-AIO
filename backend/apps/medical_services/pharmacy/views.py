from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Prescription, Medication
from .serializers import PrescriptionSerializer, MedicationSerializer


class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.select_related(
        'visit', 'visit__patient', 'doctor'
    ).prefetch_related(
        'details', 'details__medication'
    ).order_by('-prescription_date')
    serializer_class = PrescriptionSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['prescription_code', 'visit__visit_code']
    filterset_fields = ['status', 'doctor', 'visit']

    def _sync_prescription_to_billing(self, prescription):
        """Add/update prescription drug line items on the visit's invoice."""
        from apps.core_services.billing.services import BillingService
        try:
            BillingService.finalize_prescription_to_invoice(prescription)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"Failed to sync prescription {prescription.pk} to billing: {e}"
            )

    def perform_create(self, serializer):
        prescription = serializer.save()
        self._sync_prescription_to_billing(prescription)
        self._notify_pharmacist_ws(prescription, 'created')

    def perform_update(self, serializer):
        prescription = serializer.save()
        # Re-sync billing items (finalize_prescription_to_invoice skips duplicates,
        # but we need to remove stale items first when details changed)
        from apps.core_services.billing.models import InvoiceLineItem, Invoice
        from apps.core_services.billing.services import BillingService
        try:
            invoice = Invoice.objects.filter(visit=prescription.visit).first()
            if invoice:
                # Remove stale prescription items then re-add from current details
                invoice.items.filter(related_order_type='PRESCRIPTION').delete()
                invoice.calculate_totals()
                invoice.save()
            BillingService.finalize_prescription_to_invoice(prescription)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"Failed to re-sync prescription {prescription.pk} to billing: {e}"
            )


    def _notify_pharmacist_ws(self, prescription, event_type: str):
        """Broadcast WS event đến nhóm pharmacist_updates."""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        import logging
        logger = logging.getLogger(__name__)

        def _send():
            channel_layer = get_channel_layer()
            if channel_layer is None:
                logger.error("No channel layer — skipping pharmacist WS notify")
                return
            patient = prescription.visit.patient
            meds = [
                {
                    'name': d.medication.name,
                    'quantity': d.quantity,
                    'unit': d.medication.unit,
                    'usage_instruction': d.usage_instruction,
                    'duration_days': d.duration_days,
                }
                for d in prescription.details.select_related('medication').all()
            ]
            async_to_sync(channel_layer.group_send)(
                "pharmacist_updates",
                {
                    "type": "pharmacist.prescription_ready",
                    "prescription_id": str(prescription.id),
                    "prescription_code": prescription.prescription_code,
                    "visit_code": prescription.visit.visit_code,
                    "patient_name": patient.full_name if patient else '—',
                    "patient_dob": str(patient.date_of_birth) if patient and patient.date_of_birth else None,
                    "patient_gender": patient.gender if patient else None,
                    "diagnosis": prescription.diagnosis or '',
                    "note": prescription.note or '',
                    "medications": meds,
                    "total_price": str(prescription.total_price),
                    "event_type": event_type,
                    "timestamp": timezone.now().isoformat(),
                }
            )
            logger.info(f"Pharmacist WS [{event_type}] sent for prescription {prescription.prescription_code}")

        transaction.on_commit(_send)

    @action(detail=True, methods=['post'], url_path='dispense')
    def dispense(self, request, pk=None):
        """
        POST /api/v1/pharmacy/prescriptions/{id}/dispense/
        Cấp thuốc: Cập nhật đơn DISPENSED và hoàn thành lượt khám.
        """
        prescription = self.get_object()
        if prescription.status in [Prescription.Status.DISPENSED, Prescription.Status.CANCELLED]:
            return Response(
                {'detail': f'Đơn thuốc đã ở trạng thái {prescription.get_status_display()}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            prescription.status = Prescription.Status.DISPENSED
            prescription.save(update_fields=['status'])

            # Hoàn thành lượt khám
            visit = prescription.visit
            visit.status = 'COMPLETED'
            visit.save(update_fields=['status'])

        self._notify_pharmacist_ws(prescription, 'dispensed')
        return Response({'detail': 'Đã cấp thuốc thành công. Lượt khám hoàn thành.'})

    @action(detail=True, methods=['post'], url_path='refuse')
    def refuse(self, request, pk=None):
        """
        POST /api/v1/pharmacy/prescriptions/{id}/refuse/
        Bệnh nhân từ chối nhận thuốc: Hủy đơn và hoàn thành lượt khám.
        """
        prescription = self.get_object()
        if prescription.status in [Prescription.Status.DISPENSED, Prescription.Status.CANCELLED]:
            return Response(
                {'detail': f'Đơn thuốc đã ở trạng thái {prescription.get_status_display()}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            prescription.status = Prescription.Status.CANCELLED
            prescription.save(update_fields=['status'])

            # Hoàn thành lượt khám
            visit = prescription.visit
            visit.status = 'COMPLETED'
            visit.save(update_fields=['status'])

        self._notify_pharmacist_ws(prescription, 'refused')
        return Response({'detail': 'Bệnh nhân từ chối thuốc. Lượt khám hoàn thành.'})


class MedicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Catalog of Drugs
    """
    queryset = Medication.objects.filter(is_active=True).select_related('category').order_by('name')
    serializer_class = MedicationSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['code', 'name', 'active_ingredient']
    filterset_fields = ['category']


class CDSSCheckView(APIView):
    """
    POST /api/cdss/check/

    Kiểm tra CDSS cho một đơn thuốc hoặc danh sách thuốc.

    Mode 1 – Theo đơn thuốc đã tạo:
        { "prescription_id": "<uuid>" }

    Mode 2 – Kiểm tra nhanh:
        { "patient_id": "<uuid>", "medications": ["Aspirin", "Warfarin"] }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.medical_services.pharmacy.services.cdss_service import CDSSService

        data = request.data

        # Mode 1: Kiểm tra theo prescription_id
        if prescription_id := data.get('prescription_id'):
            result = CDSSService.run_cdss_check(str(prescription_id))
            if 'error' in result:
                return Response({'detail': result['error']}, status=status.HTTP_404_NOT_FOUND)
            return Response(result)

        # Mode 2: Kiểm tra nhanh
        patient_id = data.get('patient_id')
        medications = data.get('medications', [])

        if not patient_id and not medications:
            return Response(
                {'detail': 'Cần prescription_id hoặc (patient_id + medications)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(medications, list) or len(medications) == 0:
            return Response(
                {'detail': 'medications phải là danh sách không rỗng'},
                status=status.HTTP_400_BAD_REQUEST
            )

        allergy_alerts = CDSSService.check_allergy_alert(str(patient_id), medications) if patient_id else []
        interaction_alerts = CDSSService.check_drug_interaction(medications)
        has_critical = any(a['is_critical'] for a in allergy_alerts + interaction_alerts)

        return Response({
            'allergy_alerts': allergy_alerts,
            'interaction_alerts': interaction_alerts,
            'has_critical': has_critical,
        })
