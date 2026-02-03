from rest_framework import serializers
from .models import Visit
from apps.core_services.patients.serializers import PatientSerializer

class VisitSerializer(serializers.ModelSerializer):
    patient_detail = PatientSerializer(source='patient', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Visit
        fields = '__all__'
        read_only_fields = ('visit_code', 'check_in_time', 'check_out_time', 'assigned_staff', 'queue_number')

