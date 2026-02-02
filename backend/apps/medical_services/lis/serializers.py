from rest_framework import serializers
from .models import LabOrder, LabTest, LabCategory, LabOrderDetail

class LabCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LabCategory
        fields = '__all__'

class LabTestSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    class Meta:
        model = LabTest
        fields = '__all__'

class LabOrderDetailSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(source='test.name', read_only=True)
    class Meta:
        model = LabOrderDetail
        fields = '__all__'

class LabOrderSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    visit_code = serializers.CharField(source='visit.visit_code', read_only=True)
    details = LabOrderDetailSerializer(many=True, read_only=True)

    class Meta:
        model = LabOrder
        fields = '__all__'
