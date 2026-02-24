from rest_framework import serializers
from .models import FHIRServerConfig, PACSConfig, InteropAuditLog


class FHIRServerConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = FHIRServerConfig
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
        extra_kwargs = {
            'auth_token': {'write_only': True},
        }


class PACSConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PACSConfig
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
        extra_kwargs = {
            'auth_token': {'write_only': True},
        }


class InteropAuditLogSerializer(serializers.ModelSerializer):
    direction_display = serializers.CharField(
        source='get_direction_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    protocol_display = serializers.CharField(
        source='get_protocol_display', read_only=True
    )

    class Meta:
        model = InteropAuditLog
        fields = '__all__'
