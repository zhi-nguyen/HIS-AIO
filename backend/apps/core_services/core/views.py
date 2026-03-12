from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ICD10Code, ICD10Subcategory


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def icd10_search(request):
    """
    Tìm kiếm mã ICD-10 theo code hoặc tên bệnh.
    
    Query param:
        q   - Từ khóa tìm kiếm (mã ICD hoặc tên bệnh)
        limit - Số kết quả tối đa (mặc định 20)
    
    Response: [{ code, name, subcategory_code, subcategory_name }]
    """
    q = request.query_params.get('q', '').strip()
    limit = min(int(request.query_params.get('limit', 20)), 50)

    if not q or len(q) < 2:
        return Response([])

    qs = ICD10Code.objects.select_related('subcategory').filter(
        Q(code__icontains=q) | Q(name__icontains=q)
    ).order_by('code')[:limit]

    results = [
        {
            'code': item.code,
            'name': item.name,
            'subcategory_code': item.subcategory.code,
            'subcategory_name': item.subcategory.name,
        }
        for item in qs
    ]
    return Response(results)
