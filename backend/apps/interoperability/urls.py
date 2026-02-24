"""
URL Configuration cho Interoperability module.

Endpoints:
- /fhir/*        — FHIR R4 export/import
- /dicom/*       — DICOM Web proxy (QIDO/WADO/STOW)
- /interop/*     — Config & Audit
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'interop/config/fhir', views.FHIRServerConfigViewSet, basename='fhir-config')
router.register(r'interop/config/pacs', views.PACSConfigViewSet, basename='pacs-config')
router.register(r'interop/audit-log', views.InteropAuditLogViewSet, basename='interop-audit')

urlpatterns = [
    # ─── FHIR R4 Endpoints ───────────────────────────────────────────────
    path(
        'fhir/Patient/<uuid:patient_id>/',
        views.fhir_export_patient,
        name='fhir-export-patient',
    ),
    path(
        'fhir/Encounter/<uuid:visit_id>/',
        views.fhir_export_encounter,
        name='fhir-export-encounter',
    ),
    path(
        'fhir/Bundle/patient/<uuid:patient_id>/',
        views.fhir_export_patient_bundle,
        name='fhir-export-bundle',
    ),
    path(
        'fhir/import/',
        views.fhir_import,
        name='fhir-import',
    ),
    path(
        'fhir/metadata/',
        views.fhir_capability_statement,
        name='fhir-metadata',
    ),

    # ─── DICOM Web Endpoints ─────────────────────────────────────────────
    path(
        'dicom/studies/',
        views.dicom_query_studies,
        name='dicom-query-studies',
    ),
    path(
        'dicom/studies/<str:study_uid>/',
        views.dicom_retrieve_study,
        name='dicom-retrieve-study',
    ),
    path(
        'dicom/worklist/',
        views.dicom_worklist,
        name='dicom-worklist',
    ),
    path(
        'dicom/store/',
        views.dicom_store,
        name='dicom-store',
    ),

    # ─── Config & Audit Router ───────────────────────────────────────────
    path('', include(router.urls)),
]
