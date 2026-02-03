from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Visit
from .serializers import VisitSerializer
import uuid

class VisitViewSet(viewsets.ModelViewSet):
    queryset = Visit.objects.all().order_by('-check_in_time')
    serializer_class = VisitSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['visit_code', 'patient__patient_code', 'patient__first_name']
    filterset_fields = ['status', 'priority', 'patient']

    def perform_create(self, serializer):
        # Auto-generate visit_code and queue_number
        today = timezone.now().date()
        today_str = timezone.now().strftime('%Y%m%d')
        
        # Calculate queue_number for today
        today_count = Visit.objects.filter(check_in_time__date=today).count()
        queue_number = today_count + 1
        
        # Generate visit_code
        code = f"V{today_str}-{uuid.uuid4().hex[:6].upper()}"
        serializer.save(
            visit_code=code, 
            check_in_time=timezone.now(),
            queue_number=queue_number
        )

    @action(detail=True, methods=['post'])
    def triage(self, request, pk=None):
        """
        Move visit to Triage or Assign Doctor
        """
        visit = self.get_object()
        # logic to update status
        status_code = request.data.get('status')
        if status_code and status_code in Visit.Status.values:
            visit.status = status_code
            visit.save()
            return Response({'status': 'updated', 'new_status': visit.status})
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

