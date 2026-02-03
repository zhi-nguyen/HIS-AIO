from rest_framework import serializers
from .models import Prescription, PrescriptionDetail, Medication, DrugCategory

class MedicationSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    class Meta:
        model = Medication
        fields = '__all__'

class PrescriptionDetailSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    class Meta:
        model = PrescriptionDetail
        fields = '__all__'

class PrescriptionSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='visit.patient.full_name', read_only=True)
    details = PrescriptionDetailSerializer(many=True, read_only=True)
    
    class Meta:
        model = Prescription
        fields = '__all__'
