"""
QMS Views - API endpoints for Clinical Queue Management

Endpoints:
- POST /kiosk/checkin/      — Booking check-in (quét QR tại Kiosk)
- POST /walkin/checkin/      — Vãng lai lấy số
- POST /emergency/flag/      — Flag cấp cứu
- POST /doctor/call-next/    — Bác sĩ gọi BN tiếp theo
- GET  /queue/board/         — Bảng LED hàng đợi
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import QueueNumber, QueueEntry, ServiceStation, QueueStatus
from .serializers import QueueNumberSerializer, ServiceStationSerializer
from .services import ClinicalQueueService


# ====================================================================
# REST API Views for Clinical Queue
# ====================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def kiosk_checkin(request):
    """
    Bệnh nhân quét QR Booking tại Kiosk → Check-in & nhận STT ưu tiên.
    
    Request Body:
        {"appointment_id": "uuid-of-appointment", "station_id": "uuid-of-station"}
    """
    appointment_id = request.data.get('appointment_id')
    station_id = request.data.get('station_id')
    
    if not appointment_id or not station_id:
        return Response(
            {'error': 'Cần appointment_id và station_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        station = ServiceStation.objects.get(id=station_id, is_active=True)
    except ServiceStation.DoesNotExist:
        return Response(
            {'error': f'Không tìm thấy điểm dịch vụ: {station_id}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        result = ClinicalQueueService.checkin_from_booking(appointment_id, station)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'success': True,
        'message': 'Check-in thành công!',
        'queue_number': result['queue_number'].number_code,
        'daily_sequence': result['queue_number'].daily_sequence,
        'priority': result['priority'],
        'source': result['source'],
        'lateness_info': {
            'minutes': result['lateness_info']['minutes'],
            'category': result['lateness_info']['category'],
        },
        'station': {
            'code': station.code,
            'name': station.name,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def walkin_checkin(request):
    """
    Vãng lai lấy số — FCFS.
    
    Request Body:
        {
            "patient_id": "uuid-of-patient",
            "station_id": "uuid-of-station",
            "reason": "Lý do khám",
            "is_elderly_or_child": false
        }
    """
    patient_id = request.data.get('patient_id')
    station_id = request.data.get('station_id')
    reason = request.data.get('reason', '')
    is_elderly_or_child = request.data.get('is_elderly_or_child', False)
    
    if not patient_id or not station_id:
        return Response(
            {'error': 'Cần patient_id và station_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from apps.core_services.patients.models import Patient
        patient = Patient.objects.get(id=patient_id)
    except Exception:
        return Response(
            {'error': f'Không tìm thấy bệnh nhân: {patient_id}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        station = ServiceStation.objects.get(id=station_id, is_active=True)
    except ServiceStation.DoesNotExist:
        return Response(
            {'error': f'Không tìm thấy điểm dịch vụ: {station_id}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    extra_priority = ClinicalQueueService.PRIORITY_ELDERLY_CHILD_BONUS if is_elderly_or_child else 0
    
    result = ClinicalQueueService.checkin_walkin(
        patient=patient,
        station=station,
        reason=reason,
        extra_priority=extra_priority,
    )
    
    return Response({
        'success': True,
        'message': 'Lấy số thành công!',
        'queue_number': result['queue_number'].number_code,
        'daily_sequence': result['queue_number'].daily_sequence,
        'priority': result['priority'],
        'source': result['source'],
        'station': {
            'code': station.code,
            'name': station.name,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def emergency_flag(request):
    """
    Nhân viên y tế flag cấp cứu.
    
    Request Body:
        {
            "patient_id": "uuid-of-patient",
            "station_id": "uuid-of-station",
            "reason": "Lý do cấp cứu"
        }
    """
    patient_id = request.data.get('patient_id')
    station_id = request.data.get('station_id')
    reason = request.data.get('reason', 'Cấp cứu')
    
    if not patient_id or not station_id:
        return Response(
            {'error': 'Cần patient_id và station_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from apps.core_services.patients.models import Patient
        patient = Patient.objects.get(id=patient_id)
    except Exception:
        return Response(
            {'error': f'Không tìm thấy bệnh nhân: {patient_id}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        station = ServiceStation.objects.get(id=station_id, is_active=True)
    except ServiceStation.DoesNotExist:
        return Response(
            {'error': f'Không tìm thấy điểm dịch vụ: {station_id}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    result = ClinicalQueueService.flag_emergency(
        patient=patient,
        station=station,
        reason=reason,
    )
    
    return Response({
        'success': True,
        'message': '🚨 Cấp cứu đã được đăng ký!',
        'queue_number': result['queue_number'].number_code,
        'priority': result['priority'],
        'source': result['source'],
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def doctor_call_next(request):
    """
    Bác sĩ gọi bệnh nhân tiếp theo.
    
    Thuật toán: Emergency → Priority Booking → Walk-in (FCFS)
    
    Request Body:
        {"station_id": "uuid-of-station"}
    """
    station_id = request.data.get('station_id')
    
    if not station_id:
        return Response(
            {'error': 'Cần station_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        station = ServiceStation.objects.get(id=station_id, is_active=True)
    except ServiceStation.DoesNotExist:
        return Response(
            {'error': f'Không tìm thấy điểm dịch vụ: {station_id}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    result = ClinicalQueueService.call_next_patient(station)
    
    if result is None:
        return Response({
            'success': True,
            'message': 'Hàng đợi trống — không có bệnh nhân nào đang chờ.',
            'called_patient': None,
        })
    
    return Response({
        'success': True,
        'message': f"Mời {result['display_label']} - {result['patient_name']}",
        'called_patient': result,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def queue_board(request):
    """
    Bảng LED — Danh sách hàng chờ theo station (public).
    
    Query Params:
        station_id: UUID of the ServiceStation
    """
    station_id = request.query_params.get('station_id')
    
    if not station_id:
        return Response(
            {'error': 'Cần station_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        station = ServiceStation.objects.get(id=station_id, is_active=True)
    except ServiceStation.DoesNotExist:
        return Response(
            {'error': f'Không tìm thấy điểm dịch vụ: {station_id}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    board = ClinicalQueueService.get_queue_board(station)
    
    return Response({
        'success': True,
        'data': board,
    })


# ====================================================================
# Existing ViewSets (backward compatible)
# ====================================================================

class QueueNumberViewSet(viewsets.ModelViewSet):
    queryset = QueueNumber.objects.all().order_by('-created_time')
    serializer_class = QueueNumberSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['number_code', 'visit__patient__first_name']
    filterset_fields = ['station', 'created_date']

    @action(detail=False, methods=['post'])
    def call_next(self, request):
        """
        Legacy: Call next number for a station
        """
        station_id = request.data.get('station_id')
        if not station_id:
             return Response({'error': 'station_id needed'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            station = ServiceStation.objects.get(id=station_id, is_active=True)
        except ServiceStation.DoesNotExist:
            return Response({'error': 'Station not found'}, status=status.HTTP_404_NOT_FOUND)
        
        result = ClinicalQueueService.call_next_patient(station)
        if result is None:
            return Response({'message': 'Queue is empty'})
        
        return Response(result)


class ServiceStationViewSet(viewsets.ModelViewSet):
    queryset = ServiceStation.objects.filter(is_active=True)
    serializer_class = ServiceStationSerializer
