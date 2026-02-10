# apps/ai_engine/graph/tools.py
"""
Re-export Hub - Backward Compatibility

File gốc đã được tách ra các agent folder:
- consultant_agent/tools.py
- pharmacist_agent/tools.py
- triage_agent/tools.py
- paraclinical_agent/tools.py
- clinical_agent/tools.py

File này re-export tất cả để backward compatible.
"""

# Consultant Agent Tools
from apps.ai_engine.agents.consultant_agent.tools import (
    check_appointment_slots,
    open_booking_form,
    book_appointment,
)

# Clinical Agent Tools
from apps.ai_engine.agents.clinical_agent.tools import (
    save_clinical_draft,
    lookup_icd10,
)

# Pharmacist Agent Tools
from apps.ai_engine.agents.pharmacist_agent.tools import (
    check_drug_interaction,
    suggest_drug_alternative,
    InteractionSeverity,
)

# Triage Agent Tools
from apps.ai_engine.agents.triage_agent.tools import (
    trigger_emergency_alert,
    assess_vital_signs,
    TriageCode,
)

# Paraclinical Agent Tools
from apps.ai_engine.agents.paraclinical_agent.tools import (
    receive_clinical_order,
    check_contraindications,
    track_sample_status,
    check_critical_values,
    analyze_trend,
    normalize_lab_result,
    extract_imaging_conclusions,
    CriticalValueCode,
    SampleStatus,
    OrderStatus,
)