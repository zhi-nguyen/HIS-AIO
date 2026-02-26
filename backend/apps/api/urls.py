"""
URL Configuration for API App

Provides endpoints for:
- AI chat streaming (SSE and sync)
- Structured data submission for staff workflows
- Health checks
"""

from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views
from . import data_views
from apps.core_services.appointments import booking_api as booking_views
from apps.core_services.qms import views as qms_views
from apps.core_services.kiosk import views as kiosk_views
from .routers import router

app_name = 'api'

urlpatterns = [
    # ==========================================================================
    # AUTHENTICATION (JWT)
    # ==========================================================================
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # ==========================================================================
    # REST API ROUTER (CRUD)
    # ==========================================================================
    path('', include(router.urls)),

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
    # BOOKING ENDPOINTS (Patient Chatbot)
    # ==========================================================================
    path('appointments/book/', booking_views.create_booking, name='create_booking'),
    
    # ==========================================================================
    # QMS CLINICAL QUEUE ENDPOINTS
    # ==========================================================================
    path('qms/kiosk/checkin/', qms_views.kiosk_checkin, name='qms_kiosk_checkin'),
    path('qms/walkin/checkin/', qms_views.walkin_checkin, name='qms_walkin_checkin'),
    path('qms/emergency/flag/', qms_views.emergency_flag, name='qms_emergency_flag'),
    path('qms/doctor/call-next/', qms_views.doctor_call_next, name='qms_doctor_call_next'),
    path('qms/queue/board/', qms_views.queue_board, name='qms_queue_board'),
    path('qms/entries/<uuid:entry_id>/status/', qms_views.queue_entry_update_status, name='qms_entry_status'),

    # TTS Audio
    path('qms/tts/audio/<uuid:entry_id>/', qms_views.serve_tts_audio, name='qms_tts_audio'),

    # Display pairing
    path('qms/display/register/', qms_views.display_register, name='qms_display_register'),
    path('qms/display/check/', qms_views.display_check, name='qms_display_check'),
    path('qms/display/pair/', qms_views.display_pair, name='qms_display_pair'),
    
    # ==========================================================================
    # SELF-SERVICE KIOSK ENDPOINTS (3-Layer Protection)
    # ==========================================================================
    path('kiosk/identify/', kiosk_views.kiosk_identify, name='kiosk_identify'),
    path('kiosk/register/', kiosk_views.kiosk_register, name='kiosk_register'),

    # ==========================================================================
    # INSURANCE MOCK ENDPOINTS
    # ==========================================================================
    path('insurance/', include('apps.core_services.insurance_mock.urls')),

    # ==========================================================================
    # UTILITY ENDPOINTS
    # ==========================================================================
    path('health/', views.health_check, name='health_check'),
    
    # ==========================================================================
    # EMR DATA ENDPOINTS
    # ==========================================================================
    path('emr/<uuid:visit_id>/ai-suggestions/', data_views.get_ai_suggestions, name='emr_ai_suggestions'),
]

