from rest_framework import serializers
from .models import LabOrder, LabTest, LabCategory, LabOrderDetail, LabResult

class LabCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LabCategory
        fields = '__all__'

class LabTestSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    class Meta:
        model = LabTest
        fields = '__all__'

class LabResultSerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(source='technician.full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.full_name', read_only=True)
    class Meta:
        model = LabResult
        fields = '__all__'

class LabOrderDetailSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(source='test.name', read_only=True)
    test = LabTestSerializer(read_only=True)
    result = LabResultSerializer(read_only=True)
    
    class Meta:
        model = LabOrderDetail
        fields = '__all__'

class LabOrderSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_code = serializers.CharField(source='patient.patient_code', read_only=True)
    visit_code = serializers.CharField(source='visit.visit_code', read_only=True)
    details = LabOrderDetailSerializer(many=True, read_only=True)

    class Meta:
        model = LabOrder
        fields = '__all__'
