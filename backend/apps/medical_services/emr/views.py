from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import ClinicalRecord
from .serializers import ClinicalRecordSerializer

class ClinicalRecordViewSet(viewsets.ModelViewSet):
    queryset = ClinicalRecord.objects.all().order_by('-created_at')
    serializer_class = ClinicalRecordSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['visit__visit_code', 'visit__patient__patient_code']
    filterset_fields = ['doctor', 'is_finalized']

    def perform_create(self, serializer):
        # Assign current user as doctor if applicable
        # user = self.request.user
        # if hasattr(user, 'staff_profile'):
        #     serializer.save(doctor=user.staff_profile)
        # else:
        serializer.save()

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        record = self.get_object()
        if record.is_finalized:
            return Response({'error': 'Record already finalized'}, status=status.HTTP_400_BAD_REQUEST)
        
        record.is_finalized = True
        record.save()
        
        # Trigger next steps (Billing, Pharmacy, etc.) - via Signals preferably
        return Response({'status': 'finalized'})

