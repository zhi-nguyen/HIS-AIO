from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import QueueNumber, ServiceStation
from .serializers import QueueNumberSerializer, ServiceStationSerializer

class QueueNumberViewSet(viewsets.ModelViewSet):
    queryset = QueueNumber.objects.all().order_by('-created_time')
    serializer_class = QueueNumberSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['number_code', 'visit__patient__first_name']
    filterset_fields = ['station', 'created_date']

    @action(detail=False, methods=['post'])
    def call_next(self, request):
        """
        Call next number for a station
        """
        station_id = request.data.get('station_id')
        if not station_id:
             return Response({'error': 'station_id needed'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': f'Called next for station {station_id}'})

class ServiceStationViewSet(viewsets.ModelViewSet):
    queryset = ServiceStation.objects.filter(is_active=True)
    serializer_class = ServiceStationSerializer
