from rest_framework import serializers
from .models import Prescription, PrescriptionDetail, Medication, DrugCategory


class MedicationSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Medication
        fields = '__all__'


class PrescriptionDetailSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    medication_strength = serializers.CharField(source='medication.strength', read_only=True)
    medication_dosage_form = serializers.CharField(source='medication.dosage_form', read_only=True)
    medication_unit = serializers.CharField(source='medication.unit', read_only=True)

    class Meta:
        model = PrescriptionDetail
        fields = [
            'id', 'prescription', 'medication', 'medication_name',
            'medication_strength', 'medication_dosage_form', 'medication_unit',
            'quantity', 'usage_instruction', 'duration_days',
            'unit_price', 'dispensed_quantity',
        ]
        read_only_fields = ['id', 'prescription', 'dispensed_quantity']


class PrescriptionDetailWriteSerializer(serializers.Serializer):
    """Used only for writing nested details during Prescription create/update."""
    medication = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    usage_instruction = serializers.CharField(max_length=255)
    duration_days = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class PrescriptionSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='visit.patient.full_name', read_only=True)
    patient_dob = serializers.DateField(source='visit.patient.date_of_birth', read_only=True)
    patient_gender = serializers.CharField(source='visit.patient.gender', read_only=True)
    visit_code = serializers.CharField(source='visit.visit_code', read_only=True)
    details = PrescriptionDetailSerializer(many=True, read_only=True)
    # Accept nested write input
    details_input = PrescriptionDetailWriteSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Prescription
        fields = [
            'id', 'visit', 'doctor', 'prescription_code', 'prescription_date',
            'diagnosis', 'note', 'status', 'total_price',
            'ai_interaction_warning', 'cdss_alerts',
            'patient_name', 'patient_dob', 'patient_gender', 'visit_code',
            'details', 'details_input',
        ]
        read_only_fields = [
            'id', 'prescription_code', 'prescription_date', 'patient_name', 
            'patient_dob', 'patient_gender', 'visit_code', 'total_price'
        ]

    def create(self, validated_data):
        details_data = validated_data.pop('details_input', [])
        prescription = Prescription.objects.create(**validated_data)

        total = 0
        for detail_data in details_data:
            med = Medication.objects.get(pk=detail_data['medication'])
            PrescriptionDetail.objects.create(
                prescription=prescription,
                medication=med,
                quantity=detail_data['quantity'],
                usage_instruction=detail_data['usage_instruction'],
                duration_days=detail_data.get('duration_days'),
                unit_price=med.selling_price,
            )
            total += med.selling_price * detail_data['quantity']

        prescription.total_price = total
        prescription.save(update_fields=['total_price'])
        return prescription

    def update(self, instance, validated_data):
        details_data = validated_data.pop('details_input', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if details_data is not None:
            # Replace all details
            instance.details.all().delete()
            total = 0
            for detail_data in details_data:
                med = Medication.objects.get(pk=detail_data['medication'])
                PrescriptionDetail.objects.create(
                    prescription=instance,
                    medication=med,
                    quantity=detail_data['quantity'],
                    usage_instruction=detail_data['usage_instruction'],
                    duration_days=detail_data.get('duration_days'),
                    unit_price=med.selling_price,
                )
                total += med.selling_price * detail_data['quantity']
            instance.total_price = total

        instance.save()
        return instance
