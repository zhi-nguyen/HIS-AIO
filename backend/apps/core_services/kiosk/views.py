"""
Kiosk Views — API endpoints cho Kiosk tự phục vụ

Endpoints:
  POST /api/kiosk/identify/   — Quét QR CCCD/BHYT → Trả thông tin bệnh nhân
  POST /api/kiosk/register/   — Đăng ký lượt khám → Trả số thứ tự

Cả 2 endpoint đều:
  - AllowAny (không cần login, kiosk là public terminal)
  - KioskRateThrottle (10 req/min per IP)
"""

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import KioskIdentifySerializer, KioskRegisterSerializer
from .throttles import KioskRateThrottle
from .services import (
    KioskService,
    ActiveVisitExistsError,
    PatientNotFoundError,
    InvalidScanDataError,
)

logger = logging.getLogger(__name__)


# ======================================================================
# POST /api/kiosk/identify/
# ======================================================================
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([KioskRateThrottle])
def kiosk_identify(request):
    """
    Bước 1: Quét QR CCCD/BHYT → Trả thông tin bệnh nhân.
    
    Request Body:
        {"scan_data": "092200012345"}   // CCCD 12 số
        {"scan_data": "0000000123"}     // Mã BHYT mới 10 số
        {"scan_data": "TE1790000000123"} // Mã BHYT cũ 15 ký tự
    
    Response (200):
        {
            "success": true,
            "patient": {
                "id": "uuid",
                "patient_code": "BN-20260217-0001",
                "full_name": "NGUYEN VAN AN",
                "date_of_birth": "2021-03-15",
                "gender": "M",
                "is_new_patient": false
            },
            "insurance_info": {
                "insurance_code": "TE1790000000123",
                "benefit_rate": 100,
                "registered_hospital_name": "...",
                ...
            },
            "has_active_visit": false,
            "active_visit_code": null
        }
    """
    serializer = KioskIdentifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'error': serializer.errors, 'code': 'VALIDATION_ERROR'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    scan_data = serializer.validated_data['scan_data']
    
    try:
        result = KioskService.identify_patient(scan_data)
    except InvalidScanDataError as e:
        return Response(
            {'error': str(e), 'code': 'INVALID_SCAN_DATA'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except PatientNotFoundError as e:
        return Response(
            {'error': str(e), 'code': 'PATIENT_NOT_FOUND'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    patient = result['patient']
    insurance_info = result['insurance_info']
    active_visit = result['active_visit']
    
    return Response({
        'success': True,
        'patient': {
            'id': str(patient.id),
            'patient_code': patient.patient_code,
            'full_name': patient.full_name,
            'date_of_birth': str(patient.date_of_birth) if patient.date_of_birth else None,
            'gender': patient.gender,
            'is_new_patient': result['is_new_patient'],
        },
        'insurance_info': insurance_info,
        'has_active_visit': result['has_active_visit'],
        'active_visit_code': active_visit.visit_code if active_visit else None,
    })


# ======================================================================
# POST /api/kiosk/register/
# ======================================================================
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([KioskRateThrottle])
def kiosk_register(request):
    """
    Bước 2: Đăng ký lượt khám → Trả số thứ tự.
    
    Request Body:
        {
            "patient_id": "uuid-from-step-1",
            "chief_complaint": "Đau đầu, chóng mặt 2 ngày nay"
        }
    
    Response (201 - Success):
        {
            "success": true,
            "queue_number": "KIOSK-01-20260217-003",
            "daily_sequence": 3,
            "estimated_wait_minutes": 20,
            "message": "Đăng ký thành công! Số thứ tự của bạn: 3"
        }
    
    Response (409 - Active Visit Exists):
        {
            "error": "Bạn đang có một lượt khám chưa hoàn thành...",
            "code": "ACTIVE_VISIT_EXISTS",
            "active_visit_code": "VISIT-20260217-0001"
        }
    """
    serializer = KioskRegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'error': serializer.errors, 'code': 'VALIDATION_ERROR'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    patient_id = serializer.validated_data['patient_id']
    chief_complaint = serializer.validated_data['chief_complaint']
    
    try:
        result = KioskService.register_visit(
            patient_id=patient_id,
            chief_complaint=chief_complaint,
        )
    except PatientNotFoundError as e:
        return Response(
            {'error': str(e), 'code': 'PATIENT_NOT_FOUND'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ActiveVisitExistsError as e:
        return Response(
            {
                'error': str(e),
                'code': 'ACTIVE_VISIT_EXISTS',
                'active_visit_code': e.visit.visit_code,
            },
            status=status.HTTP_409_CONFLICT
        )
    except Exception as e:
        logger.exception(f"[KIOSK] Register error: {e}")
        return Response(
            {'error': 'Đã xảy ra lỗi hệ thống. Vui lòng thử lại.', 'code': 'SERVER_ERROR'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response({
        'success': True,
        'visit_code': result['visit'].visit_code,
        'queue_number': result['queue_number'],
        'daily_sequence': result['daily_sequence'],
        'estimated_wait_minutes': result['estimated_wait_minutes'],
        'message': result['message'],
    }, status=status.HTTP_201_CREATED)
