from typing import Dict, Any, List
from django.db.models import Prefetch

from apps.core_services.reception.models import Visit
from apps.medical_services.emr.models import ClinicalRecord
from apps.medical_services.paraclinical.models import ServiceResult, ServiceOrder

class PatientContextBuilder:
    @staticmethod
    def build_context(visit_id: str) -> Dict[str, Any]:
        """
        Build a comprehensive context dictionary for the AI agent.
        Includes patient info, visit history, and recent lab results.
        """
        try:
            current_visit = Visit.objects.select_related('patient').get(id=visit_id)
            patient = current_visit.patient
        except Visit.DoesNotExist:
            return {"error": "Visit not found"}

        context = {
            "patient": {
                "id": str(patient.id),
                "name": patient.full_name,
                "dob": str(patient.date_of_birth),
                "gender": patient.gender,
                "phone": patient.contact_number,
                "address": patient.address_detail,
            },
            "current_visit": {
                "visit_code": current_visit.visit_code,
                "reason": "N/A", # Default, can be populated if ClinicalRecord exists
                "vitals": {},
            },
            "medical_history": [],
            "lab_results": []
        }

        # 1. Current Clinical Details
        try:
            clinical_record = ClinicalRecord.objects.get(visit=current_visit)
            context["current_visit"]["reason"] = clinical_record.chief_complaint
            context["current_visit"]["vitals"] = clinical_record.vital_signs
        except ClinicalRecord.DoesNotExist:
            pass

        # 2. Historical Visits (Last 5)
        last_visits = Visit.objects.filter(
            patient=patient, 
            status=Visit.Status.COMPLETED
        ).exclude(id=visit_id).order_by('-created_at')[:5]

        for v in last_visits:
            summary = "N/A"
            try:
                rec = ClinicalRecord.objects.get(visit=v)
                summary = rec.final_diagnosis or rec.chief_complaint
            except ClinicalRecord.DoesNotExist:
                pass
            
            context["medical_history"].append({
                "date": v.created_at.strftime("%Y-%m-%d"),
                "diagnosis": summary
            })

        # 3. Recent Lab Results (Current Visit)
        results = ServiceResult.objects.filter(
            order__visit=current_visit,
            order__status=ServiceOrder.Status.COMPLETED
        ).select_related('order__service')

        for res in results:
            context["lab_results"].append({
                "service": res.order.service.name,
                "result": res.text_result or "See Image",
                "ai_analysis": res.ai_analysis_json
            })
            
        # 4. Allergy Info (Mock - assuming schema doesn't support it yet widely)
        # context["allergies"] = patient.allergies # If field exists

        return context
