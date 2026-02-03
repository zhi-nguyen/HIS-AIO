from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import ServiceCatalog
from .serializers import ServiceCatalogSerializer

class ServiceCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for Service Catalog (Staff search services)
    """
    queryset = ServiceCatalog.objects.filter(is_active=True).order_by('name')
    serializer_class = ServiceCatalogSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['code', 'name']
    filterset_fields = ['service_type']
