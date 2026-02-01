from typing import List, Dict
from .models import Medication

class PharmacyService:
    @staticmethod
    def check_inventory(medication_ids: List[str]) -> Dict[str, int]:
        """
        Check inventory levels for a list of medication IDs.
        Returns a dict: {medication_name: current_inventory_count}
        """
        inventory_status = {}
        medications = Medication.objects.filter(id__in=medication_ids)
        
        for med in medications:
            inventory_status[med.name] = med.inventory_count
            
        return inventory_status

    @staticmethod
    def validate_interactions(medication_ids: List[str]) -> List[str]:
        """
        Mock function to check drug interactions.
        In a real system, this would query a dedicated drug database or external API.
        """
        warnings = []
        medications = Medication.objects.filter(id__in=medication_ids)
        med_names = [m.name.lower() for m in medications]
        
        # Mock logic for demonstration
        if "aspirin" in med_names and "warfarin" in med_names:
            warnings.append("High risk of bleeding: Aspirin + Warfarin")
            
        if "ibuprofen" in med_names and "aspirin" in med_names:
            warnings.append("Reduced antiplatelet effect of Aspirin when taken with Ibuprofen")

        return warnings
