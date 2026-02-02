from rest_framework import serializers
from .models import ImagingOrder, ImagingProcedure, Modality

class ModalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Modality
        fields = '__all__'

class ImagingProcedureSerializer(serializers.ModelSerializer):
    modality_name = serializers.CharField(source='modality.name', read_only=True)
    class Meta:
        model = ImagingProcedure
        fields = '__all__'

class ImagingOrderSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    procedure_name = serializers.CharField(source='procedure.name', read_only=True)
    
    class Meta:
        model = ImagingOrder
        fields = '__all__'
