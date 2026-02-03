from rest_framework import serializers
from .models import QueueNumber, QueueEntry, ServiceStation

class ServiceStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceStation
        fields = '__all__'

class QueueNumberSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)
    visit_code = serializers.CharField(source='visit.visit_code', read_only=True)
    patient_name = serializers.CharField(source='visit.patient.full_name', read_only=True)

    class Meta:
        model = QueueNumber
        fields = '__all__'

class QueueEntrySerializer(serializers.ModelSerializer):
    number_code = serializers.CharField(source='queue_number.number_code', read_only=True)
    
    class Meta:
        model = QueueEntry
        fields = '__all__'
