from django.utils import timezone
from .models import Visit
from apps.medical_services.emr.models import ClinicalRecord

class ReceptionService:
    @staticmethod
    def create_visit(patient, reason: str, priority: str = 'NORMAL') -> Visit:
        """
        Create a new visit for a patient.
        """
        # Generate a simple visit code (In production, use a sequence or UUID logic)
        today_str = timezone.now().strftime('%Y%m%d')
        count = Visit.objects.filter(created_at__date=timezone.now().date()).count() + 1
        visit_code = f"VISIT-{today_str}-{count:04d}"

        visit = Visit.objects.create(
            patient=patient,
            visit_code=visit_code,
            priority=priority,
            check_in_time=timezone.now(),
            status=Visit.Status.CHECK_IN,
            queue_number=count
        )
        
        # Initialize Clinical Record automatically
        ClinicalRecord.objects.create(
            visit=visit,
            doctor=None, # Will be assigned later
            chief_complaint=reason
        )
        
        return visit

    @staticmethod
    def update_vitals(visit_id: str, vitals_data: dict) -> ClinicalRecord:
        """
        Update vital signs in the ClinicalRecord.
        vitals_data example: {"bp": "120/80", "hr": 80, "temp": 37.0}
        """
        visit = Visit.objects.get(id=visit_id)
        # Ensure clinical record exists (it should from create_visit)
        record, created = ClinicalRecord.objects.get_or_create(visit=visit)
        
        current_vitals = record.vital_signs or {}
        current_vitals.update(vitals_data)
        
        record.vital_signs = current_vitals
        record.save(update_fields=['vital_signs'])
        
        return record
