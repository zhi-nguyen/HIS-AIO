from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .models import LabOrder, LabTest, LabOrderDetail, LabResult
from .serializers import LabOrderSerializer, LabTestSerializer


def _get_staff(request):
    """
    Lấy Staff instance từ request.user.
    User và Staff là 2 model riêng — liên kết qua staff_profile (OneToOneField).
    Trả về None nếu user chưa có Staff profile (tránh crash).
    """
    if not request.user or not request.user.is_authenticated:
        return None
    try:
        return request.user.staff_profile
    except Exception:
        return None


class LabOrderViewSet(viewsets.ModelViewSet):
    queryset = LabOrder.objects.all().order_by('-order_time')
    serializer_class = LabOrderSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['visit__visit_code', 'patient__patient_code']
    filterset_fields = ['status', 'doctor', 'visit']
    pagination_class = None

    @action(detail=True, methods=['post'])
    def results(self, request, pk=None):
        """Nhập/cập nhật kết quả xét nghiệm cho từng chỉ số"""
        order = self.get_object()
        results_data = request.data.get('results', [])
        errors = []
        technician = _get_staff(request)  # Staff instance, không phải User

        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"DEBUG HIT RESULTS API! Data keys: {request.data.keys()}")
        logger.warning(f"DEBUG results_data length: {len(results_data)}")

        for res in results_data:
            detail_id = res.get('detail_id')
            value_string = res.get('value_string', '')
            value_numeric = res.get('value_numeric')
            
            logger.warning(f"DEBUG processing detail_id: {detail_id}, val_str: {value_string}, val_num: {value_numeric}")

            try:
                detail = order.details.get(id=detail_id)
                res_obj, created = LabResult.objects.update_or_create(
                    detail=detail,
                    defaults={
                        'value_string': value_string,
                        'value_numeric': value_numeric,
                        'technician': technician,
                    }
                )
                logger.warning(f"DEBUG saved result ID: {res_obj.id}")
            except LabOrderDetail.DoesNotExist:
                logger.error(f"DEBUG detail_id {detail_id} DOES NOT EXIST")
                errors.append(f"Không tìm thấy chi tiết detail_id={detail_id} trong phiếu này")
                continue
            except Exception as e:
                logger.error(f"DEBUG EXCEPTION: {e}")

        # Tự động cập nhật trạng thái sang PROCESSING nếu còn PENDING
        if order.status == LabOrder.Status.PENDING:
            order.status = LabOrder.Status.PROCESSING
            order.save()

        serializer = self.get_serializer(order)
        response_data = serializer.data
        if errors:
            response_data['warnings'] = errors
        return Response(response_data)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Bác sĩ xét nghiệm duyệt kết quả — đổi trạng thái sang COMPLETED"""
        order = self.get_object()

        # Kiểm tra đã có kết quả chưa
        details_with_result = [d for d in order.details.all() if hasattr(d, 'result')]
        if not details_with_result:
            return Response(
                {'detail': 'Chưa có kết quả nào được nhập. Vui lòng nhập kết quả trước khi duyệt.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Duyệt từng kết quả — dùng Staff instance, không phải User
        technician = _get_staff(request)
        for detail in details_with_result:
            result = detail.result
            result.is_verified = True
            result.verified_by = technician
            result.save()

        # Cập nhật trạng thái order sang VERIFIED → trigger WebSocket signal
        order.status = LabOrder.Status.VERIFIED
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)


class LabTestViewSet(viewsets.ReadOnlyModelViewSet):
    """Catalog of Lab Tests"""
    queryset = LabTest.objects.all().order_by('category', 'name')
    serializer_class = LabTestSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['code', 'name']
    filterset_fields = ['category']
