"""
FHIR R4 Parsers — chuyển đổi FHIR R4 JSON → internal Django models.

Hướng nhận dữ liệu từ hệ thống bên ngoài (Import).
Parser sẽ tìm record tồn tại (theo identifier) hoặc tạo mới.
"""

import logging
from typing import Optional

from .resources import (
    SYSTEM_PATIENT_CODE, SYSTEM_CCCD, SYSTEM_BHYT,
    RESOURCE_PATIENT, RESOURCE_DIAGNOSTIC_REPORT,
)

logger = logging.getLogger(__name__)


def _find_identifier(identifiers: list, system: str) -> Optional[str]:
    """Extract value from a list of FHIR identifiers matching a given system."""
    for ident in identifiers:
        if ident.get('system') == system:
            return ident.get('value')
    return None


def _reverse_gender(fhir_gender: str) -> str:
    """Map FHIR gender → internal gender code."""
    reverse = {'male': 'M', 'female': 'F', 'other': 'O', 'unknown': 'O'}
    return reverse.get(fhir_gender, 'O')


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR Patient → Internal Patient
# ═══════════════════════════════════════════════════════════════════════════════

def parse_fhir_patient(fhir_data: dict) -> dict:
    """
    Parse a FHIR Patient resource → dict of internal Patient field values.

    Does NOT create the model instance directly — returns a dict that can be
    used with Patient.objects.update_or_create().

    Args:
        fhir_data: dict representing a FHIR Patient resource

    Returns:
        dict with keys:
            - 'lookup': dict for lookup (update_or_create kwargs)
            - 'defaults': dict of field values
    """
    assert fhir_data.get('resourceType') == RESOURCE_PATIENT, \
        f"Expected Patient, got {fhir_data.get('resourceType')}"

    identifiers = fhir_data.get('identifier', [])

    # Lookup by patient_code first, then by id_card
    patient_code = _find_identifier(identifiers, SYSTEM_PATIENT_CODE)
    id_card = _find_identifier(identifiers, SYSTEM_CCCD)
    insurance_number = _find_identifier(identifiers, SYSTEM_BHYT)

    # Name
    names = fhir_data.get('name', [{}])
    official_name = next(
        (n for n in names if n.get('use') == 'official'),
        names[0] if names else {}
    )
    last_name = official_name.get('family', '')
    given_names = official_name.get('given', [])
    first_name = given_names[0] if given_names else ''

    # Contact
    telecoms = fhir_data.get('telecom', [])
    phone = next(
        (t.get('value') for t in telecoms if t.get('system') == 'phone'),
        None
    )

    defaults = {
        'first_name': first_name,
        'last_name': last_name,
        'gender': _reverse_gender(fhir_data.get('gender', 'unknown')),
        'date_of_birth': fhir_data.get('birthDate'),
    }

    if id_card:
        defaults['id_card'] = id_card
    if insurance_number:
        defaults['insurance_number'] = insurance_number
    if phone:
        defaults['contact_number'] = phone

    # Determine lookup field
    lookup = {}
    if patient_code:
        lookup['patient_code'] = patient_code
    elif id_card:
        lookup['id_card'] = id_card
    else:
        # Use FHIR resource id as fallback (generate patient_code)
        fhir_id = fhir_data.get('id', '')
        lookup['patient_code'] = f'FHIR-{fhir_id[:12]}'

    return {
        'lookup': lookup,
        'defaults': defaults,
    }


def apply_parsed_patient(parsed: dict):
    """
    Apply parsed FHIR Patient data to create or update an internal Patient.

    Args:
        parsed: dict returned by parse_fhir_patient()

    Returns:
        tuple: (Patient instance, created: bool)
    """
    from apps.core_services.patients.models import Patient

    patient, created = Patient.objects.update_or_create(
        **parsed['lookup'],
        defaults=parsed['defaults'],
    )

    action = 'Created' if created else 'Updated'
    logger.info(f"{action} Patient {patient.patient_code} from FHIR import")

    return patient, created


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR DiagnosticReport → Log import (kết quả xét nghiệm từ bên ngoài)
# ═══════════════════════════════════════════════════════════════════════════════

def parse_fhir_diagnostic_report(fhir_data: dict) -> dict:
    """
    Parse a FHIR DiagnosticReport → structured dict for manual processing.

    Note: Automatic creation of LabOrder/LabResult is complex and depends on
    matching internal LabTest definitions. This parser extracts the data
    for review/manual import.

    Args:
        fhir_data: dict representing a FHIR DiagnosticReport resource

    Returns:
        dict with parsed report information
    """
    assert fhir_data.get('resourceType') == RESOURCE_DIAGNOSTIC_REPORT, \
        f"Expected DiagnosticReport, got {fhir_data.get('resourceType')}"

    # Extract observations from contained resources
    contained = {
        r['id']: r
        for r in fhir_data.get('contained', [])
        if r.get('resourceType') == 'Observation'
    }

    observations = []
    for ref in fhir_data.get('result', []):
        ref_id = ref.get('reference', '').lstrip('#')
        obs_data = contained.get(ref_id)
        if obs_data:
            observations.append({
                'code': _extract_code(obs_data.get('code', {})),
                'value': _extract_value(obs_data),
                'interpretation': _extract_interpretation(obs_data),
                'reference_range': _extract_reference_range(obs_data),
            })

    return {
        'report_id': fhir_data.get('id'),
        'status': fhir_data.get('status'),
        'category': _extract_code(
            fhir_data.get('category', [{}])[0] if fhir_data.get('category') else {}
        ),
        'issued': fhir_data.get('issued'),
        'observations': observations,
    }


def _extract_code(codeable_concept: dict) -> dict:
    """Extract coding info from a CodeableConcept."""
    codings = codeable_concept.get('coding', [])
    if codings:
        c = codings[0]
        return {
            'system': c.get('system', ''),
            'code': c.get('code', ''),
            'display': c.get('display', ''),
        }
    return {'text': codeable_concept.get('text', '')}


def _extract_value(observation: dict) -> Optional[dict]:
    """Extract value from an Observation."""
    if 'valueQuantity' in observation:
        vq = observation['valueQuantity']
        return {
            'value': vq.get('value'),
            'unit': vq.get('unit', ''),
        }
    if 'valueString' in observation:
        return {'value': observation['valueString'], 'unit': ''}
    return None


def _extract_interpretation(observation: dict) -> Optional[str]:
    """Extract interpretation from an Observation."""
    interpretations = observation.get('interpretation', [])
    if interpretations:
        codings = interpretations[0].get('coding', [])
        if codings:
            return codings[0].get('code', '')
    return None


def _extract_reference_range(observation: dict) -> Optional[dict]:
    """Extract reference range from an Observation."""
    ranges = observation.get('referenceRange', [])
    if ranges:
        rr = ranges[0]
        result = {}
        if 'low' in rr:
            result['low'] = rr['low'].get('value')
        if 'high' in rr:
            result['high'] = rr['high'].get('value')
        return result if result else None
    return None
