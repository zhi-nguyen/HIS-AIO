# apps/ai_engine/graph/llm_config.py

from langchain_google_genai import ChatGoogleGenerativeAI
from google.oauth2 import service_account
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
    lookup_department,
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
# CONFIGURATION — đọc từ Django settings (= .env)
# Chỉ cần sửa .env là toàn bộ agents dùng model mới
# ==============================================================================
from django.conf import settings as django_settings
import os

MODEL_CONFIG = {
    "complex": getattr(django_settings, 'AGENT_COMPLEX_MODEL', 'gemini-2.0-flash'),
    "fast":    getattr(django_settings, 'AGENT_FAST_MODEL',    'gemini-2.0-flash'),
}

TEMPERATURE_CONFIG = {
    "creative": getattr(django_settings, 'AGENT_TEMPERATURE', 0.7),
    "precise":  0.2,
}

# ==============================================================================
# VERTEX AI CREDENTIALS
# ==============================================================================
_creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
_vertex_project = getattr(django_settings, 'VERTEX_AI_PROJECT', 'xiaoyue-api')
_vertex_location = getattr(django_settings, 'VERTEX_AI_LOCATION', 'us-central1')

_credentials = None
if _creds_path and os.path.exists(_creds_path):
    _credentials = service_account.Credentials.from_service_account_file(
        _creds_path,
        scopes=['https://www.googleapis.com/auth/cloud-platform'],
    )

# ==============================================================================
# MODELS  (Vertex AI backend)
# ==============================================================================

# Model for Complex Reasoning (Clinical, Triage, Supervisor)
llm_pro = ChatGoogleGenerativeAI(
    model=MODEL_CONFIG["complex"],
    temperature=TEMPERATURE_CONFIG["precise"],
    convert_system_message_to_human=True,
    streaming=True,
    project=_vertex_project,
    location=_vertex_location,
    credentials=_credentials,
)

# Model for Fast Tasks (Consultant, Marketing, Summarize)
llm_flash = ChatGoogleGenerativeAI(
    model=MODEL_CONFIG["fast"],
    temperature=TEMPERATURE_CONFIG["creative"],
    convert_system_message_to_human=True,
    streaming=True,
    project=_vertex_project,
    location=_vertex_location,
    credentials=_credentials,
)

# ==============================================================================
# TOOLS BINDING
# ==============================================================================

consultant_tools = [check_appointment_slots, open_booking_form]
pharmacist_tools = [check_drug_interaction, suggest_drug_alternative]
# Triage chỉ cần lookup_department — trigger_emergency_alert gọi tự động trong code
triage_tools = [lookup_department]
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
