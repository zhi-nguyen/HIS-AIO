from rest_framework import serializers
from .models import Patient

class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ('patient_code', 'is_merged', 'merged_into')
