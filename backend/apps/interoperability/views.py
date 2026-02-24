"""
API Views cho Interoperability module.

Cung cấp endpoints cho:
- FHIR: Export/Import resources, CapabilityStatement
- DICOM: PACS proxy (QIDO/WADO/STOW), Worklist
- Config: FHIR/PACS server management, Audit log
"""

import json
import time
import logging

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import FHIRServerConfig, PACSConfig, InteropAuditLog
from .serializers import (
    FHIRServerConfigSerializer,
    PACSConfigSerializer,
    InteropAuditLogSerializer,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fhir_export_patient(request, patient_id):
    """Export a Patient as FHIR R4 Patient resource."""
    from apps.core_services.patients.models import Patient
    from .fhir.mappers import map_patient_to_fhir

    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response(
            {'error': f'Patient {patient_id} not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    fhir_resource = map_patient_to_fhir(patient)

    _log_interop(
        direction='OUT', protocol='FHIR',
        resource_type='Patient', resource_id=str(patient_id),
        status_val='SUCCESS',
    )

    return Response(fhir_resource, content_type='application/fhir+json')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fhir_export_encounter(request, visit_id):
    """Export a Visit as FHIR R4 Encounter resource."""
    from apps.core_services.reception.models import Visit
    from .fhir.mappers import map_visit_to_encounter

    try:
        visit = Visit.objects.select_related(
            'patient', 'confirmed_department',
        ).get(id=visit_id)
    except Visit.DoesNotExist:
        return Response(
            {'error': f'Visit {visit_id} not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    fhir_resource = map_visit_to_encounter(visit)

    _log_interop(
        direction='OUT', protocol='FHIR',
        resource_type='Encounter', resource_id=str(visit_id),
        status_val='SUCCESS',
    )

    return Response(fhir_resource, content_type='application/fhir+json')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fhir_export_patient_bundle(request, patient_id):
    """Export full FHIR Bundle containing all resources for a patient."""
    from apps.core_services.patients.models import Patient
    from .fhir.mappers import build_patient_bundle

    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response(
            {'error': f'Patient {patient_id} not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    start = time.time()
    bundle = build_patient_bundle(patient)
    duration_ms = int((time.time() - start) * 1000)

    _log_interop(
        direction='OUT', protocol='FHIR',
        resource_type='Bundle', resource_id=str(patient_id),
        status_val='SUCCESS', duration_ms=duration_ms,
    )

    return Response(bundle, content_type='application/fhir+json')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fhir_import(request):
    """
    Import one or more FHIR resources.
    Supports: Patient, DiagnosticReport.
    """
    from .fhir.parsers import parse_fhir_patient, apply_parsed_patient
    from .fhir.parsers import parse_fhir_diagnostic_report

    data = request.data
    if not isinstance(data, dict):
        return Response(
            {'error': 'Expected a FHIR resource JSON object'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resource_type = data.get('resourceType')
    start = time.time()

    try:
        if resource_type == 'Patient':
            parsed = parse_fhir_patient(data)
            patient, created = apply_parsed_patient(parsed)
            result = {
                'status': 'created' if created else 'updated',
                'patient_id': str(patient.id),
                'patient_code': patient.patient_code,
            }

        elif resource_type == 'DiagnosticReport':
            parsed = parse_fhir_diagnostic_report(data)
            result = {
                'status': 'parsed',
                'data': parsed,
                'message': 'DiagnosticReport parsed. Manual review needed for lab mapping.',
            }

        elif resource_type == 'Bundle':
            # Process Bundle entries
            results = []
            entries = data.get('entry', [])
            for entry in entries:
                resource = entry.get('resource', {})
                rt = resource.get('resourceType')
                if rt == 'Patient':
                    parsed = parse_fhir_patient(resource)
                    patient, created = apply_parsed_patient(parsed)
                    results.append({
                        'resourceType': 'Patient',
                        'status': 'created' if created else 'updated',
                        'id': str(patient.id),
                    })
                else:
                    results.append({
                        'resourceType': rt,
                        'status': 'skipped',
                        'message': f'{rt} import not yet supported',
                    })
            result = {'status': 'processed', 'entries': results}

        else:
            return Response(
                {'error': f'Unsupported resource type: {resource_type}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        duration_ms = int((time.time() - start) * 1000)
        _log_interop(
            direction='IN', protocol='FHIR',
            resource_type=resource_type,
            resource_id=data.get('id', ''),
            status_val='SUCCESS', duration_ms=duration_ms,
        )

        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        _log_interop(
            direction='IN', protocol='FHIR',
            resource_type=resource_type or 'Unknown',
            status_val='FAILED', duration_ms=duration_ms,
            error_message=str(e),
        )
        logger.exception("FHIR import failed")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fhir_capability_statement(request):
    """
    Return FHIR CapabilityStatement (metadata endpoint).
    Mô tả các resource types mà HIS hỗ trợ.
    """
    from .fhir.resources import SUPPORTED_RESOURCES

    statement = {
        'resourceType': 'CapabilityStatement',
        'status': 'active',
        'kind': 'instance',
        'fhirVersion': '4.0.1',
        'format': ['json'],
        'software': {
            'name': 'HIS-AIO',
            'version': '1.0.0',
        },
        'implementation': {
            'description': 'HIS All-in-One FHIR Adapter',
        },
        'rest': [{
            'mode': 'server',
            'resource': [
                {
                    'type': rt,
                    'interaction': [
                        {'code': 'read'},
                        {'code': 'search-type'},
                    ],
                }
                for rt in SUPPORTED_RESOURCES
            ],
        }],
    }

    return Response(statement, content_type='application/fhir+json')


# ═══════════════════════════════════════════════════════════════════════════════
# DICOM ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dicom_query_studies(request):
    """
    QIDO-RS proxy: Query studies from PACS.
    Query params: patient_id, patient_name, study_date, modality, limit, offset
    """
    from .dicom.client import DICOMWebClient

    client = DICOMWebClient.from_config()

    studies = client.query_studies(
        patient_id=request.query_params.get('patient_id'),
        patient_name=request.query_params.get('patient_name'),
        study_date=request.query_params.get('study_date'),
        modality=request.query_params.get('modality'),
        limit=int(request.query_params.get('limit', 20)),
        offset=int(request.query_params.get('offset', 0)),
    )

    _log_interop(
        direction='OUT', protocol='DICOM',
        resource_type='Study', status_val='SUCCESS',
    )

    return Response({'studies': studies, 'count': len(studies)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dicom_retrieve_study(request, study_uid):
    """
    WADO-RS proxy: Retrieve study metadata from PACS.
    """
    from .dicom.wado import get_study_image_urls

    result = get_study_image_urls(study_uid)

    if not result.get('found'):
        return Response(
            {'error': f'Study {study_uid} not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    _log_interop(
        direction='OUT', protocol='DICOM',
        resource_type='Study', resource_id=study_uid,
        status_val='SUCCESS',
    )

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dicom_worklist(request):
    """
    Get Modality Worklist entries for pending imaging orders.
    Query params: modality, ae_title
    """
    from .dicom.worklist import generate_worklist_entries

    entries = generate_worklist_entries(
        modality_code=request.query_params.get('modality'),
        ae_title=request.query_params.get('ae_title'),
    )

    return Response({'entries': entries, 'count': len(entries)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dicom_store(request):
    """
    STOW-RS proxy: Store a DICOM instance to PACS.
    Expects raw DICOM file in request body.
    """
    from .dicom.client import DICOMWebClient

    if not request.body:
        return Response(
            {'error': 'No DICOM data in request body'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    client = DICOMWebClient.from_config()
    result = client.store_instance(request.body)

    status_val = 'SUCCESS' if result.get('status') == 'success' else 'FAILED'
    _log_interop(
        direction='OUT', protocol='DICOM',
        resource_type='Instance', status_val=status_val,
        error_message=result.get('error'),
    )

    http_status = (
        status.HTTP_200_OK
        if result.get('status') == 'success'
        else status.HTTP_502_BAD_GATEWAY
    )

    return Response(result, status=http_status)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG + AUDIT ViewSets
# ═══════════════════════════════════════════════════════════════════════════════

class FHIRServerConfigViewSet(viewsets.ModelViewSet):
    queryset = FHIRServerConfig.objects.all().order_by('-created_at')
    serializer_class = FHIRServerConfigSerializer


class PACSConfigViewSet(viewsets.ModelViewSet):
    queryset = PACSConfig.objects.all().order_by('-created_at')
    serializer_class = PACSConfigSerializer


class InteropAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InteropAuditLog.objects.all()
    serializer_class = InteropAuditLogSerializer
    filterset_fields = ['protocol', 'direction', 'status', 'resource_type']


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _log_interop(
    direction: str,
    protocol: str,
    resource_type: str,
    status_val: str,
    resource_id: str = None,
    duration_ms: int = None,
    error_message: str = None,
):
    """Create an audit log entry."""
    try:
        InteropAuditLog.objects.create(
            direction=direction,
            protocol=protocol,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status_val,
            duration_ms=duration_ms,
            error_message=error_message,
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
