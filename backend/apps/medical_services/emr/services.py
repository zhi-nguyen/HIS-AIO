from django.utils import timezone
from .models import ClinicalRecord
from apps.core_services.reception.models import Visit

class ClinicalService:
    @staticmethod
    def save_draft_diagnosis(visit_id: str, diagnosis_data: dict) -> ClinicalRecord:
        """
        Update ClinicalRecord with draft data.
        diagnosis_data keys: chief_complaint, history_of_present_illness, physical_exam, treatment_plan
        """
        record = ClinicalRecord.objects.get(visit__id=visit_id)
        
        if 'chief_complaint' in diagnosis_data:
            record.chief_complaint = diagnosis_data['chief_complaint']
        
        if 'history_of_present_illness' in diagnosis_data:
            record.history_of_present_illness = diagnosis_data['history_of_present_illness']
            
        if 'physical_exam' in diagnosis_data:
            record.physical_exam = diagnosis_data['physical_exam']
            
        if 'treatment_plan' in diagnosis_data:
            record.treatment_plan = diagnosis_data['treatment_plan']
            
        if 'final_diagnosis' in diagnosis_data:
            record.final_diagnosis = diagnosis_data['final_diagnosis']
            
        if 'main_icd' in diagnosis_data:
            record.main_icd = diagnosis_data['main_icd']

        record.save()
        return record

    @staticmethod
    def finalize_visit(visit_id: str) -> ClinicalRecord:
        """
        Mark the visit as completed and the record as finalized.
        """
        record = ClinicalRecord.objects.get(visit__id=visit_id)
        visit = record.visit
        
        # 1. Lock the clinical record
        record.is_finalized = True
        record.save(update_fields=['is_finalized'])
        
        # 2. Update visit status
        visit.status = Visit.Status.COMPLETED
        visit.check_out_time = timezone.now()
        visit.save(update_fields=['status', 'check_out_time'])
        
        return record
