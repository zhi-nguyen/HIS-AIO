from rest_framework import viewsets, filters, status
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
    filterset_fields = ['status', 'doctor']

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

