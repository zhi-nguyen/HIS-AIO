from django.utils import timezone
from django.db import transaction, IntegrityError
from .models import Visit
from apps.medical_services.emr.models import ClinicalRecord

class ReceptionService:
    @staticmethod
    def create_visit(patient, reason: str, priority: str = 'NORMAL') -> Visit:
        """
        Create a new visit for a patient.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        today_str = timezone.now().strftime('%Y%m%d')
        count = Visit.objects.filter(created_at__date=timezone.now().date()).count() + 1

        max_retries = 10
        visit = None
        for attempt in range(max_retries):
            visit_code = f"VISIT-{today_str}-{count:04d}"
            try:
                with transaction.atomic():
                    visit = Visit.objects.create(
                        patient=patient,
                        visit_code=visit_code,
                        priority=priority,
                        check_in_time=timezone.now(),
                        status=Visit.Status.CHECK_IN,
                        queue_number=count
                    )
                break  # Success
            except IntegrityError:
                count += 1
                logger.warning(
                    f"[RECEPTION] visit_code {visit_code} conflict, "
                    f"retrying with count={count} (attempt {attempt + 1})"
                )
        
        if visit is None:
            raise Exception(
                f"Không thể tạo mã lượt khám sau {max_retries} lần thử."
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
