from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import LabOrder, LabTest
from .serializers import LabOrderSerializer, LabTestSerializer

class LabOrderViewSet(viewsets.ModelViewSet):
    queryset = LabOrder.objects.all().order_by('-order_time')
    serializer_class = LabOrderSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['visit__visit_code', 'patient__patient_code']
    filterset_fields = ['status', 'doctor']

class LabTestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Catalog of Lab Tests
    """
    queryset = LabTest.objects.all().order_by('category', 'name')
    serializer_class = LabTestSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['code', 'name']
    filterset_fields = ['category']

