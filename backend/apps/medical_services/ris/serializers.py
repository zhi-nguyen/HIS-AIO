from rest_framework import serializers
from .models import (
    Modality, ImagingProcedure, ImagingOrder, 
    ImagingExecution, ImagingResult
)


class ModalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Modality
        fields = '__all__'


class ImagingProcedureSerializer(serializers.ModelSerializer):
    modality_name = serializers.CharField(source='modality.name', read_only=True)

    class Meta:
        model = ImagingProcedure
        fields = '__all__'


class ImagingExecutionSerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(
        source='technician.full_name', read_only=True, default=None
    )

    class Meta:
        model = ImagingExecution
        fields = [
            'id', 'order', 'technician', 'technician_name',
            'execution_time', 'machine_id', 'dicom_study_uid', 'orthanc_instance_id',
            'thumbnail_url', 'execution_note',
        ]
        read_only_fields = ['id', 'execution_time']


class ImagingResultSerializer(serializers.ModelSerializer):
    radiologist_name = serializers.CharField(
        source='radiologist.full_name', read_only=True, default=None
    )
    verified_by_name = serializers.CharField(
        source='verified_by.full_name', read_only=True, default=None
    )

    class Meta:
        model = ImagingResult
        fields = [
            'id', 'order', 'findings', 'conclusion', 'recommendation',
            'radiologist', 'radiologist_name', 'report_time',
            'is_verified', 'verified_by', 'verified_by_name', 'verified_time',
            'is_abnormal', 'is_critical',
        ]
        read_only_fields = ['id', 'report_time', 'verified_time']


class ImagingOrderSerializer(serializers.ModelSerializer):
    """
    Serializer chính cho ImagingOrder — bao gồm nested execution và result.
    """
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_code = serializers.CharField(source='patient.patient_code', read_only=True)
    procedure_name = serializers.CharField(source='procedure.name', read_only=True)
    modality_code = serializers.CharField(source='procedure.modality.code', read_only=True)
    modality_name = serializers.CharField(source='procedure.modality.name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    visit_code = serializers.CharField(source='visit.visit_code', read_only=True)

    # Nested read-only
    execution = ImagingExecutionSerializer(read_only=True)
    result = ImagingResultSerializer(read_only=True)

    # Status display
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = ImagingOrder
        fields = [
            'id', 'visit', 'visit_code', 'patient', 'patient_name', 'patient_code',
            'doctor', 'doctor_name', 'procedure', 'procedure_name',
            'modality_code', 'modality_name',
            'clinical_indication', 'accession_number',
            'order_time', 'scheduled_time',
            'status', 'status_display', 'priority', 'priority_display',
            'price_at_time', 'note',
            'execution', 'result',
        ]
        read_only_fields = ['id', 'order_time']
