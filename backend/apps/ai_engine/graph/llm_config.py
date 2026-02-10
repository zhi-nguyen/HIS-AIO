# apps/ai_engine/graph/llm_config.py

from langchain_google_genai import ChatGoogleGenerativeAI
from apps.ai_engine.agents.consultant_agent.tools import (
    check_appointment_slots,
    open_booking_form,
    book_appointment,
)
from apps.ai_engine.agents.pharmacist_agent.tools import (
    check_drug_interaction,
    suggest_drug_alternative,
)
from apps.ai_engine.agents.triage_agent.tools import (
    trigger_emergency_alert,
    assess_vital_signs,
)
from apps.ai_engine.agents.paraclinical_agent.tools import (
    receive_clinical_order,
    check_contraindications,
    track_sample_status,
    check_critical_values,
    analyze_trend,
    normalize_lab_result,
    extract_imaging_conclusions,
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

MODEL_CONFIG = {
    "complex": "gemini-2.0-flash", # Using flash for dev, typically pro
    "fast": "gemini-2.0-flash"
}

TEMPERATURE_CONFIG = {
    "creative": 0.7,
    "precise": 0.2
}

# ==============================================================================
# MODELS
# ==============================================================================

# Model for Complex Reasoning (Clinical, Triage, Supervisor)
llm_pro = ChatGoogleGenerativeAI(
    model=MODEL_CONFIG["complex"],
    temperature=TEMPERATURE_CONFIG["precise"],
    convert_system_message_to_human=True,
    streaming=True  # Enable token-by-token streaming
)

# Model for Fast Tasks (Consultant, Marketing, Summarize)
llm_flash = ChatGoogleGenerativeAI(
    model=MODEL_CONFIG["fast"],
    temperature=TEMPERATURE_CONFIG["creative"],
    convert_system_message_to_human=True,
    streaming=True  # Enable token-by-token streaming
)

# ==============================================================================
# TOOLS BINDING
# ==============================================================================

consultant_tools = [check_appointment_slots, open_booking_form]
pharmacist_tools = [check_drug_interaction, suggest_drug_alternative]
triage_tools = [trigger_emergency_alert, assess_vital_signs]
paraclinical_tools = [
    receive_clinical_order,
    check_contraindications,
    track_sample_status,
    check_critical_values,
    analyze_trend,
    normalize_lab_result,
    extract_imaging_conclusions,
]

llm_consultant_with_tools = llm_flash.bind_tools(consultant_tools)
llm_pharmacist_with_tools = llm_flash.bind_tools(pharmacist_tools)
llm_triage_with_tools = llm_pro.bind_tools(triage_tools)
llm_paraclinical_with_tools = llm_pro.bind_tools(paraclinical_tools)

def logging_node_execution(node_name: str):
    """Log execution of a node."""
    print(f"--- Executing Node: {node_name} ---")
