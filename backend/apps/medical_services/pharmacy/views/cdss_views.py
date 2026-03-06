"""
REST API views cho CDSS (Clinical Decision Support System).

Track 3: Endpoint cho frontend hiển thị cảnh báo dị ứng và tương tác thuốc
trước khi bác sĩ xác nhận đơn thuốc.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


class CDSSCheckView(APIView):
    """
    POST /api/cdss/check/

    Kiểm tra CDSS cho một đơn thuốc hoặc danh sách thuốc.

    Request body (chọn 1 trong 2 mode):

    Mode 1 – Kiểm tra theo đơn thuốc đã tạo:
        { "prescription_id": "<uuid>" }

    Mode 2 – Kiểm tra nhanh trước khi tạo đơn:
        {
            "patient_id": "<uuid>",
            "medications": ["Aspirin", "Warfarin", "Metformin"]
        }

    Response:
        {
            "allergy_alerts": [...],
            "interaction_alerts": [...],
            "has_critical": bool
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.medical_services.pharmacy.services.cdss_service import CDSSService

        data = request.data

        # Mode 1: Kiểm tra theo prescription_id (đơn đã tạo)
        if prescription_id := data.get('prescription_id'):
            result = CDSSService.run_cdss_check(str(prescription_id))
            if 'error' in result:
                return Response(
                    {'detail': result['error']},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(result)

        # Mode 2: Kiểm tra nhanh theo patient + danh sách thuốc
        patient_id = data.get('patient_id')
        medications = data.get('medications', [])

        if not patient_id and not medications:
            return Response(
                {'detail': 'Cần cung cấp prescription_id hoặc (patient_id + medications)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(medications, list) or len(medications) == 0:
            return Response(
                {'detail': 'medications phải là danh sách tên thuốc không rỗng'},
                status=status.HTTP_400_BAD_REQUEST
            )

        allergy_alerts = []
        if patient_id:
            allergy_alerts = CDSSService.check_allergy_alert(str(patient_id), medications)

        interaction_alerts = CDSSService.check_drug_interaction(medications)

        has_critical = any(
            a['is_critical'] for a in allergy_alerts + interaction_alerts
        )

        return Response({
            'allergy_alerts': allergy_alerts,
            'interaction_alerts': interaction_alerts,
            'has_critical': has_critical,
        })
