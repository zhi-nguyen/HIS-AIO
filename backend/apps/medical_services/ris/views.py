from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import ImagingOrder, ImagingProcedure
from .serializers import ImagingOrderSerializer, ImagingProcedureSerializer

class ImagingOrderViewSet(viewsets.ModelViewSet):
    queryset = ImagingOrder.objects.all().order_by('-order_time')
    serializer_class = ImagingOrderSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['visit__visit_code', 'patient__patient_code']
    filterset_fields = ['status', 'doctor', 'procedure__modality']

class ImagingProcedureViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImagingProcedure.objects.all().order_by('modality', 'name')
    serializer_class = ImagingProcedureSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['code', 'name']
    filterset_fields = ['modality']

