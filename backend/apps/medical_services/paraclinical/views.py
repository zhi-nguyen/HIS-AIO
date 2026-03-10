import json
import logging

import django_filters
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import ServiceList, ServiceOrder
from .serializers import ServiceListSerializer, ServiceOrderSerializer
from .services import OrderingService

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Mapping nhóm dịch vụ → danh sách category trong DB
# ──────────────────────────────────────────────────────────────
SERVICE_GROUP_CATEGORIES = {
    'xet_nghiem': [
        'Huyết học',
        'Sinh hóa',
        'Miễn dịch',
        'Vi sinh',
        'XN',
        'LAB',
    ],
    'chan_doan_hinh_anh': [
        'CĐHA',
        'Thăm dò chức năng',
        'CDHA',
        'IMAGING',
    ],
}


class ServiceOrderFilter(django_filters.FilterSet):
    """
    FilterSet tùy chỉnh cho ServiceOrder.

    Tham số đặc biệt:
    - service_group=xet_nghiem          → lọc xét nghiệm (LIS)
    - service_group=chan_doan_hinh_anh  → lọc CĐHA/Thăm dò (RIS-CLS)
    - service__category=<tên>           → lọc từng category cụ thể
    """
    service_group = django_filters.CharFilter(method='filter_service_group', label='Nhóm dịch vụ')

    class Meta:
        model = ServiceOrder
        fields = ['visit', 'status', 'service__category']

    def filter_service_group(self, queryset, name, value):
        categories = SERVICE_GROUP_CATEGORIES.get(value)
        if categories:
            return queryset.filter(service__category__in=categories)
        return queryset


class ServiceListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Danh mục dịch vụ CLS (Cận Lâm Sàng)
    GET /api/v1/cls/services/       — Lấy tất cả
    GET /api/v1/cls/services/?category=Sinh hóa  — Lọc theo danh mục
    GET /api/v1/cls/services/?search=glucose      — Tìm theo mã/tên
    """
    queryset = ServiceList.objects.all().order_by('category', 'name')
    serializer_class = ServiceListSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['code', 'name']
    filterset_fields = ['category']
    pagination_class = None  # Trả hết, catalog nhỏ


class ServiceOrderViewSet(viewsets.ModelViewSet):
    """
    Phiếu chỉ định CLS
    GET /api/v1/cls/orders/?visit=<uuid>               — Theo lượt khám
    GET /api/v1/cls/orders/?service_group=xet_nghiem   — Chỉ XN (LIS)
    GET /api/v1/cls/orders/?service_group=chan_doan_hinh_anh — Chỉ CĐHA (RIS-CLS)
    """
    queryset = ServiceOrder.objects.all().select_related(
        'service', 'requester', 'requester__user', 'visit__patient'
    ).order_by('-created_at')
    serializer_class = ServiceOrderSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['service__name', 'service__code', 'visit__visit_code']
    filterset_class = ServiceOrderFilter


@csrf_exempt
@require_http_methods(["POST"])
def batch_create_orders(request):
    """
    Tạo nhiều chỉ định CLS cùng lúc cho 1 lượt khám.

    POST /api/v1/cls/batch-order/
    Body: { "visit_id": "<uuid>", "service_ids": ["<uuid>", ...] }

    Response: { "success": true, "orders": [...], "duplicates": [...] }
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
        visit_id = body.get('visit_id')
        service_ids = body.get('service_ids', [])

        if not visit_id:
            return JsonResponse(
                {'error': 'visit_id là bắt buộc', 'code': 'MISSING_VISIT_ID'},
                status=400
            )
        if not service_ids:
            return JsonResponse(
                {'error': 'service_ids không được rỗng', 'code': 'MISSING_SERVICES'},
                status=400
            )

        # Kiểm tra trùng lặp trước khi tạo
        duplicates = OrderingService.check_duplicate_orders(visit_id, service_ids)
        if duplicates:
            return JsonResponse({
                'success': False,
                'error': 'Có dịch vụ đã được chỉ định',
                'duplicates': duplicates,
            }, status=409, json_dumps_params={'ensure_ascii': False})

        # Lấy requester từ request user (cần ID của Staff chứ không phải User)
        requester_id = None
        if request.user.is_authenticated:
            try:
                requester_id = str(request.user.staff_profile.id)
            except Exception:
                pass
                
        if not requester_id:
            # Fallback: dùng user đầu tiên (dev mode)
            from apps.core_services.authentication.models import Staff
            staff = Staff.objects.first()
            requester_id = str(staff.id) if staff else None

        orders = OrderingService.create_lab_order(visit_id, service_ids, requester_id)

        # Serialize response
        order_data = []
        for order in orders:
            order_data.append({
                'id': str(order.id),
                'service_name': order.service.name,
                'service_code': order.service.code,
                'price': str(order.service.price),
                'status': order.status,
                'priority': order.priority,
            })

        return JsonResponse({
            'success': True,
            'orders': order_data,
            'count': len(order_data),
        }, json_dumps_params={'ensure_ascii': False})

    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'JSON không hợp lệ', 'code': 'INVALID_JSON'},
            status=400
        )
    except Exception as e:
        logger.error(f"Batch order error: {e}", exc_info=True)
        return JsonResponse(
            {'error': str(e), 'code': 'INTERNAL_ERROR'},
            status=500, json_dumps_params={'ensure_ascii': False}
        )
