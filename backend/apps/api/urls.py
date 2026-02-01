"""
URL Configuration for API App

Provides endpoints for:
- AI chat streaming (SSE and sync)
- Structured data submission for staff workflows
- Health checks
"""

from django.urls import path
from . import views
from . import data_views

app_name = 'api'

urlpatterns = [
    # ==========================================================================
    # CHAT ENDPOINTS (Streaming)
    # ==========================================================================
    path('chat/stream/', views.chat_stream, name='chat_stream'),
    path('chat/sync/', views.chat_sync, name='chat_sync'),
    
    # ==========================================================================
    # STRUCTURED DATA ENDPOINTS (Staff Workflows)
    # ==========================================================================
    
    # Triage Assessment - Submit patient data for AI triage
    path('triage/assess/', data_views.submit_triage_assessment, name='triage_assess'),
    
    # Vital Signs - Quick rule-based assessment (no LLM)
    path('vitals/assess/', data_views.assess_vitals, name='vitals_assess'),
    
    # Drug Interactions - Check medication lists
    path('pharmacy/interactions/', data_views.check_drug_interactions, name='drug_interactions'),
    
    # Lab Orders - Create lab orders with contraindication check
    path('lab/order/', data_views.create_lab_order, name='lab_order'),
    
    # Patient Summary - Generate summaries from EMR data
    path('patient/summary/', data_views.generate_patient_summary, name='patient_summary'),
    
    # ==========================================================================
    # UTILITY ENDPOINTS
    # ==========================================================================
    path('health/', views.health_check, name='health_check'),
    
    # ==========================================================================
    # EMR DATA ENDPOINTS
    # ==========================================================================
    path('emr/<uuid:visit_id>/ai-suggestions/', data_views.get_ai_suggestions, name='emr_ai_suggestions'),
]

