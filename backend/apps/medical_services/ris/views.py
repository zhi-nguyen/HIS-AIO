import logging
from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import ImagingOrder, ImagingProcedure, ImagingExecution, ImagingResult
from .serializers import (
    ImagingOrderSerializer, ImagingProcedureSerializer,
    ImagingExecutionSerializer, ImagingResultSerializer,
)

logger = logging.getLogger(__name__)


def _get_staff(request):
    """
    Lấy Staff instance từ request.user.
    User và Staff là 2 model riêng — liên kết qua staff_profile (OneToOneField).
    """
    if not request.user or not request.user.is_authenticated:
        return None
    try:
        return request.user.staff_profile
    except Exception:
        return None


class ImagingOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet quản lý phiếu chỉ định CĐHA (ImagingOrder).
    Hỗ trợ: CRUD + actions start_execution / save_result / verify.
    """
    queryset = ImagingOrder.objects.select_related(
        'patient', 'visit', 'doctor', 'procedure', 'procedure__modality'
    ).prefetch_related(
        'execution', 'result'
    ).all().order_by('-order_time')

    serializer_class = ImagingOrderSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['visit__visit_code', 'patient__patient_code', 'accession_number']
    filterset_fields = ['status', 'doctor', 'procedure__modality', 'priority', 'visit']
    pagination_class = None

    # ------------------------------------------------------------------
    # ACTION: Bắt đầu chụp — KTV tạo ImagingExecution
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def start_execution(self, request, pk=None):
        """KTV bắt đầu chụp — tạo ImagingExecution, đổi status → IN_PROGRESS."""
        order = self.get_object()

        if order.status not in [ImagingOrder.Status.PENDING, ImagingOrder.Status.SCHEDULED]:
            return Response(
                {'detail': f'Không thể bắt đầu chụp khi trạng thái là {order.get_status_display()}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        technician = _get_staff(request)
        machine_id = request.data.get('machine_id', '')

        execution, created = ImagingExecution.objects.get_or_create(
            order=order,
            defaults={
                'technician': technician,
                'machine_id': machine_id,
            }
        )

        if not created:
            return Response(
                {'detail': 'Ca chụp này đã được bắt đầu trước đó.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = ImagingOrder.Status.IN_PROGRESS
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # ACTION: Lưu kết quả đọc phim — BS CĐHA nhập findings/conclusion
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def save_result(self, request, pk=None):
        """BS CĐHA nhập/cập nhật kết quả đọc phim (findings, conclusion)."""
        order = self.get_object()

        findings = request.data.get('findings', '')
        conclusion = request.data.get('conclusion', '')
        recommendation = request.data.get('recommendation', '')
        is_abnormal = request.data.get('is_abnormal', False)
        is_critical = request.data.get('is_critical', False)

        if not findings or not conclusion:
            return Response(
                {'detail': 'Cần nhập cả mô tả hình ảnh (findings) và kết luận (conclusion).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        radiologist = _get_staff(request)

        result, created = ImagingResult.objects.update_or_create(
            order=order,
            defaults={
                'findings': findings,
                'conclusion': conclusion,
                'recommendation': recommendation,
                'radiologist': radiologist,
                'is_abnormal': is_abnormal,
                'is_critical': is_critical,
            }
        )

        # Cập nhật status → REPORTED (đã có kết quả, chờ duyệt)
        if order.status in [ImagingOrder.Status.COMPLETED, ImagingOrder.Status.IN_PROGRESS]:
            order.status = ImagingOrder.Status.REPORTED
            order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # ACTION: Duyệt kết quả — BS duyệt, đổi status → VERIFIED
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """BS duyệt kết quả CĐHA — đổi trạng thái sang VERIFIED."""
        order = self.get_object()

        # Kiểm tra đã có kết quả chưa
        try:
            result = order.result
        except ImagingResult.DoesNotExist:
            return Response(
                {'detail': 'Chưa có kết quả đọc phim. Vui lòng nhập kết quả trước khi duyệt.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        verifier = _get_staff(request)
        result.is_verified = True
        result.verified_by = verifier
        result.verified_time = timezone.now()
        result.save()

        order.status = ImagingOrder.Status.VERIFIED
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)


class ImagingProcedureViewSet(viewsets.ReadOnlyModelViewSet):
    """Danh mục kỹ thuật CĐHA (chỉ đọc)."""
    queryset = ImagingProcedure.objects.select_related('modality').all().order_by('modality', 'name')
    serializer_class = ImagingProcedureSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['code', 'name']
    filterset_fields = ['modality']


# ==========================================================================
# WEBHOOK ENDPOINT — Nhận tín hiệu từ Orthanc khi có ảnh DICOM mới
# ==========================================================================
@api_view(['POST'])
@permission_classes([AllowAny])
def orthanc_webhook(request):
    """
    Webhook nhận HTTP POST từ Orthanc (OnStableStudy Lua script).
    Không xử lý data ngay — đẩy vào Celery task để xử lý bất đồng bộ.

    Payload từ Orthanc:
    {
        "orthanc_id": "...",
        "study_instance_uid": "1.2.3...",
        "accession_number": "ACC001",
        "patient_id": "PID001",
        "patient_name": "Nguyen Van A",
        "study_description": "CT Chest",
        "number_of_series": 3
    }
    """
    data = request.data
    study_uid = data.get('study_instance_uid')
    orthanc_id = data.get('orthanc_id')

    if not study_uid:
        logger.warning("Orthanc webhook: Missing study_instance_uid")
        return Response(
            {'detail': 'Missing study_instance_uid'},
            status=status.HTTP_400_BAD_REQUEST
        )

    logger.info(
        f"Orthanc webhook received: study_uid={study_uid}, "
        f"orthanc_id={orthanc_id}, "
        f"accession={data.get('accession_number')}"
    )

    # Đẩy vào Celery task — trả về 200 OK ngay lập tức
    from .tasks import process_dicom_study
    process_dicom_study.delay(
        study_uid=study_uid,
        orthanc_id=orthanc_id,
        accession_number=data.get('accession_number', ''),
        patient_id=data.get('patient_id', ''),
        patient_name=data.get('patient_name', ''),
        study_description=data.get('study_description', ''),
        number_of_series=data.get('number_of_series', 0),
    )

    return Response({'status': 'accepted', 'study_uid': study_uid})
