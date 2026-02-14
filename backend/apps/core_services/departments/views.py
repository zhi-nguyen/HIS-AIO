from rest_framework import viewsets
from .models import Department
from .serializers import DepartmentSerializer


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet cho danh sách Khoa.
    Chỉ cho phép đọc (list, retrieve).
    """
    queryset = Department.objects.filter(is_active=True).order_by('code')
    serializer_class = DepartmentSerializer
    pagination_class = None  # Trả về toàn bộ, không phân trang
