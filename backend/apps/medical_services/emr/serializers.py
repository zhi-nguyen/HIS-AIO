from rest_framework import serializers
from .models import ClinicalRecord, ICD10Code
from apps.core_services.reception.serializers import VisitSerializer

class ICD10CodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ICD10Code
        fields = '__all__'

class ClinicalRecordSerializer(serializers.ModelSerializer):
    visit_detail = VisitSerializer(source='visit', read_only=True)
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    main_icd_code = serializers.CharField(source='main_icd.code', read_only=True)
    main_icd_name = serializers.CharField(source='main_icd.name', read_only=True)

    class Meta:
        model = ClinicalRecord
        fields = '__all__'
        read_only_fields = ('visit', 'doctor', 'is_finalized', 'triage_agent_summary', 'clinical_agent_summary')
