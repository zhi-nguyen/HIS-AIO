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


def _broadcast_queue_update(station):
    """
    Push the full queue board to all WebSocket-connected displays for this station.
    Safe to call from sync context (views).
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        board = ClinicalQueueService.get_queue_board(station)
        async_to_sync(channel_layer.group_send)(
            f'qms_station_{station.id}',
            {
                'type': 'queue_update',
                'data': board,
            },
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Failed to broadcast queue update')


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

    # TTS: generate audio for this patient
    try:
        from apps.core_services.qms.tts_service import generate_tts_audio
        generate_tts_audio.delay(str(result['queue_entry'].id))
    except Exception:
        pass  # TTS is best-effort

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

    # TTS: generate audio for this patient
    try:
        from apps.core_services.qms.tts_service import generate_tts_audio
        generate_tts_audio.delay(str(result['queue_entry'].id))
    except Exception:
        pass  # TTS is best-effort
    
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

    # Max concurrent calls reached
    if 'error' in result:
        return Response({
            'success': False,
            'message': result['error'],
            'active_count': result.get('active_count', 0),
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    _broadcast_queue_update(station)

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
    
    import logging
    logger = logging.getLogger('qms')

    try:
        board = ClinicalQueueService.get_queue_board(station)
    except Exception as exc:
        logger.exception('get_queue_board crashed for station %s: %s', station_id, exc)
        return Response(
            {'error': f'Lỗi khi tải bảng chờ: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    
    return Response({
        'success': True,
        'data': board,
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def queue_entry_update_status(request, entry_id):
    """
    Cập nhật trạng thái QueueEntry (Hoàn thành / Bỏ qua / Không có mặt).

    PATCH /qms/entries/<entry_id>/status/
    Request Body:
        {"status": "COMPLETED"} hoặc {"status": "SKIPPED"} hoặc {"status": "NO_SHOW"}
    """
    VALID_STATUSES = ('COMPLETED', 'SKIPPED', 'NO_SHOW', 'CALLED')
    STATUS_MESSAGES = {
        'COMPLETED': 'Hoàn thành phục vụ',
        'SKIPPED': 'Đã bỏ qua',
        'NO_SHOW': 'Đã gọi nhưng không có mặt',
        'CALLED': 'Đã gọi lại bệnh nhân',
    }

    new_status = request.data.get('status')

    if new_status not in VALID_STATUSES:
        return Response(
            {'error': f'status phải là một trong: {", ".join(VALID_STATUSES)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        entry = QueueEntry.objects.select_related(
            'queue_number', 'station'
        ).get(id=entry_id)
    except QueueEntry.DoesNotExist:
        return Response(
            {'error': f'Không tìm thấy phiếu xếp hàng: {entry_id}'},
            status=status.HTTP_404_NOT_FOUND,
        )

    entry.status = new_status
    if new_status == 'CALLED':
        # Re-call: xóa end_time, đặt lại called_time
        entry.end_time = None
        entry.called_time = timezone.now()
        entry.save(update_fields=['status', 'end_time', 'called_time'])
    else:
        entry.end_time = timezone.now()
        entry.save(update_fields=['status', 'end_time'])

    _broadcast_queue_update(entry.station)

    return Response({
        'success': True,
        'message': STATUS_MESSAGES.get(new_status, '\u0110\u00e3 c\u1eadp nh\u1eadt'),
        'entry_id': str(entry.id),
        'queue_number': entry.queue_number.number_code,
        'status': new_status,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def serve_tts_audio(request, entry_id):
    """
    Serve pre-generated TTS audio for a QueueEntry.

    GET /qms/tts/audio/<entry_id>/
    Returns: MP3 file (audio/mpeg) or 404
    """
    from django.http import FileResponse
    from apps.core_services.qms.tts_service import get_audio_url, _get_redis_client
    import os

    r = _get_redis_client()
    redis_key = f'tts:audio:{entry_id}'
    file_path = r.get(redis_key)

    if file_path and os.path.exists(file_path):
        return FileResponse(
            open(file_path, 'rb'),
            content_type='audio/mpeg',
            as_attachment=False,
            filename=os.path.basename(file_path),
        )

    return Response(
        {'error': 'Audio not found or not yet generated'},
        status=status.HTTP_404_NOT_FOUND,
    )


# ====================================================================
# Existing ViewSets (backward compatible)
# ====================================================================

class QueueNumberViewSet(viewsets.ModelViewSet):
    serializer_class = QueueNumberSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['number_code', 'visit__patient__first_name']
    filterset_fields = ['station', 'created_date']

    def get_queryset(self):
        qs = QueueNumber.objects.all().select_related(
            'station', 'visit__patient',
        ).prefetch_related('entries').order_by('-created_time')

        # Support ?status= filter through QueueEntry
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(entries__status=status_param)

        return qs

    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /qms/queues/<id>/
        Supports { "status": "COMPLETED" } and { "status": "SKIPPED" }
        by updating the related QueueEntry.
        """
        queue_number = self.get_object()
        new_status = request.data.get('status')

        if new_status in ('COMPLETED', 'SKIPPED'):
            # Find the active entry (WAITING, CALLED, or IN_PROGRESS)
            entry = queue_number.entries.filter(
                status__in=[
                    QueueStatus.WAITING,
                    QueueStatus.CALLED,
                    QueueStatus.IN_PROGRESS,
                ]
            ).order_by('-entered_queue_time').first()

            if entry:
                entry.status = new_status
                entry.end_time = timezone.now()
                entry.save(update_fields=['status', 'end_time'])

            # Return updated queue number with status
            serializer = self.get_serializer(queue_number)
            data = serializer.data
            data['status'] = new_status
            data['entry_id'] = str(entry.id) if entry else None
            return Response(data)

        # Default behavior for other fields
        return super().partial_update(request, *args, **kwargs)

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

    def get_queryset(self):
        qs = super().get_queryset()
        station_type = self.request.query_params.get('station_type')
        if station_type:
            qs = qs.filter(station_type=station_type)
        return qs


# ====================================================================
# Display Pairing System
# ====================================================================

import random, string, logging
logger = logging.getLogger(__name__)

# In-memory pairing store: { code: { station_id, station_name, paired_at } }
_display_pairings = {}


@api_view(['POST'])
@permission_classes([AllowAny])
def display_register(request):
    """
    Display screen registers itself with a new pairing code.
    POST /qms/display/register/
    Returns: { code: "ABC123" }
    """
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    _display_pairings[code] = {'station_id': None, 'station_name': None}
    return Response({'code': code})


@api_view(['GET'])
@permission_classes([AllowAny])
def display_check(request):
    """
    Display polls to check if its code has been paired.
    GET /qms/display/check/?code=ABC123
    Returns: { paired: true/false, station_id, station_name }
    """
    code = request.query_params.get('code', '').upper()
    entry = _display_pairings.get(code)
    if not entry:
        return Response({'paired': False, 'error': 'Code not found'})
    if entry['station_id']:
        return Response({
            'paired': True,
            'station_id': entry['station_id'],
            'station_name': entry['station_name'],
        })
    return Response({'paired': False})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def display_pair(request):
    """
    Reception pairs a display code to a station.
    POST /qms/display/pair/
    Body: { code: "ABC123", station_id: "uuid" }
    """
    code = (request.data.get('code') or '').upper()
    station_id = request.data.get('station_id')

    if not code or not station_id:
        return Response(
            {'error': 'code và station_id là bắt buộc'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    entry = _display_pairings.get(code)
    if not entry:
        return Response(
            {'error': f'Mã "{code}" không tồn tại hoặc đã hết hạn'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        station = ServiceStation.objects.get(id=station_id)
    except ServiceStation.DoesNotExist:
        return Response(
            {'error': 'Điểm dịch vụ không tồn tại'},
            status=status.HTTP_404_NOT_FOUND,
        )

    entry['station_id'] = str(station.id)
    entry['station_name'] = station.name
    logger.info(f'Display paired: code={code} → station={station.code}')

    return Response({
        'success': True,
        'message': f'Đã liên kết màn hình với {station.name}',
        'station_id': str(station.id),
        'station_name': station.name,
    })
