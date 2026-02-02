from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Prescription, Medication
from .serializers import PrescriptionSerializer, MedicationSerializer

class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.all().order_by('-prescription_date')
    serializer_class = PrescriptionSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['prescription_code', 'visit__visit_code']
    filterset_fields = ['status', 'doctor']

class MedicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Catalog of Drugs
    """
    queryset = Medication.objects.filter(is_active=True).order_by('name')
    serializer_class = MedicationSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['code', 'name', 'active_ingredient']
    filterset_fields = ['category']
