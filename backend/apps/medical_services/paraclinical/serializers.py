from rest_framework import serializers
from .models import ServiceList, ServiceOrder


class ServiceListSerializer(serializers.ModelSerializer):
    """Serializer cho danh mục dịch vụ CLS"""
    class Meta:
        model = ServiceList
        fields = ['id', 'code', 'name', 'price', 'category']


class ServiceOrderSerializer(serializers.ModelSerializer):
    """Serializer cho phiếu chỉ định CLS"""
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_code = serializers.CharField(source='service.code', read_only=True)
    service_price = serializers.DecimalField(
        source='service.price', max_digits=10, decimal_places=2, read_only=True
    )
    service_category = serializers.CharField(source='service.category', read_only=True)
    requester_name = serializers.SerializerMethodField()

    # Thông tin lượt khám và bệnh nhân (cho trang LIS/RIS)
    visit_code = serializers.CharField(source='visit.visit_code', read_only=True)
    patient_code = serializers.CharField(source='visit.patient.patient_code', read_only=True)
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'visit', 'service', 'status', 'priority',
            'clinical_note', 'created_at',
            'service_name', 'service_code', 'service_price', 'service_category',
            'requester_name',
            # Nested visit/patient info
            'visit_code', 'patient_code', 'patient_name',
        ]
        read_only_fields = ['id', 'created_at']

    def get_requester_name(self, obj):
        """Staff không phải AbstractUser — lấy tên qua FK user"""
        try:
            user = obj.requester.user
            full = user.get_full_name()  # AbstractUser method (first_name + last_name)
            return full if full.strip() else user.username
        except Exception:
            return None

    def get_patient_name(self, obj):
        """Lấy tên đầy đủ của bệnh nhân từ visit.patient"""
        try:
            patient = obj.visit.patient
            # Patient model có property full_name = last_name + first_name
            name = f"{patient.last_name} {patient.first_name}".strip()
            return name if name else None
        except Exception:
            return None
