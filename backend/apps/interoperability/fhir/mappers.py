"""
FHIR R4 Mappers — chuyển đổi internal Django models → FHIR R4 JSON.

Mỗi hàm nhận một Django model instance và trả về một dict
tương thích chuẩn FHIR R4 (có thể serialize trực tiếp thành JSON).

Sử dụng:
    from apps.interoperability.fhir.mappers import map_patient_to_fhir
    fhir_json = map_patient_to_fhir(patient_instance)
"""

from datetime import date
from typing import Optional

from .resources import (
    SYSTEM_PATIENT_CODE, SYSTEM_CCCD, SYSTEM_BHYT, SYSTEM_VISIT_CODE,
    SYSTEM_ICD10, SYSTEM_LOINC, SYSTEM_DICOM_UID,
    GENDER_MAP, ENCOUNTER_STATUS_MAP, ENCOUNTER_CLASS_MAP,
    DIAGNOSTIC_REPORT_STATUS_MAP, VITAL_SIGN_LOINC, MODALITY_MAP,
    RESOURCE_PATIENT, RESOURCE_ENCOUNTER, RESOURCE_CONDITION,
    RESOURCE_OBSERVATION, RESOURCE_DIAGNOSTIC_REPORT,
    RESOURCE_IMAGING_STUDY, RESOURCE_BUNDLE,
    build_reference, build_identifier, build_codeable_concept, build_coding,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PATIENT → FHIR Patient
# ═══════════════════════════════════════════════════════════════════════════════

def map_patient_to_fhir(patient) -> dict:
    """
    Map Patient model → FHIR R4 Patient resource.

    Args:
        patient: apps.core_services.patients.models.Patient instance

    Returns:
        dict: FHIR Patient resource
    """
    resource = {
        'resourceType': RESOURCE_PATIENT,
        'id': str(patient.id),
        'identifier': [
            build_identifier(SYSTEM_PATIENT_CODE, patient.patient_code),
        ],
        'active': patient.is_active,
        'name': [{
            'use': 'official',
            'family': patient.last_name,
            'given': [patient.first_name],
            'text': patient.full_name,
        }],
        'gender': GENDER_MAP.get(patient.gender, 'unknown'),
    }

    # Ngày sinh
    if patient.date_of_birth:
        resource['birthDate'] = patient.date_of_birth.isoformat()

    # CCCD
    if patient.id_card:
        resource['identifier'].append(
            build_identifier(SYSTEM_CCCD, patient.id_card)
        )

    # Bảo hiểm y tế
    if patient.insurance_number:
        resource['identifier'].append(
            build_identifier(SYSTEM_BHYT, patient.insurance_number)
        )

    # Số điện thoại
    if patient.contact_number:
        resource['telecom'] = [{
            'system': 'phone',
            'value': patient.contact_number,
            'use': 'mobile',
        }]

    # Địa chỉ
    address = _build_address(patient)
    if address:
        resource['address'] = [address]

    return resource


def _build_address(patient) -> Optional[dict]:
    """Build FHIR Address from Patient address fields."""
    parts = []
    addr = {}

    if patient.address_detail:
        addr['line'] = [patient.address_detail]
        parts.append(patient.address_detail)

    if patient.ward:
        addr['district'] = patient.ward.name
        parts.append(patient.ward.name)

    if patient.province:
        addr['state'] = patient.province.name
        parts.append(patient.province.name)

    if parts:
        addr['text'] = ', '.join(parts)
        addr['country'] = 'VN'
        return addr

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# VISIT → FHIR Encounter
# ═══════════════════════════════════════════════════════════════════════════════

def map_visit_to_encounter(visit) -> dict:
    """
    Map Visit model → FHIR R4 Encounter resource.

    Args:
        visit: apps.core_services.reception.models.Visit instance

    Returns:
        dict: FHIR Encounter resource
    """
    encounter_class = ENCOUNTER_CLASS_MAP.get(
        visit.priority, ENCOUNTER_CLASS_MAP['NORMAL']
    )

    resource = {
        'resourceType': RESOURCE_ENCOUNTER,
        'id': str(visit.id),
        'identifier': [
            build_identifier(SYSTEM_VISIT_CODE, visit.visit_code),
        ],
        'status': ENCOUNTER_STATUS_MAP.get(visit.status, 'unknown'),
        'class': build_coding(
            'http://terminology.hl7.org/CodeSystem/v3-ActCode',
            encounter_class['code'],
            encounter_class['display'],
        ),
        'subject': build_reference(RESOURCE_PATIENT, str(visit.patient_id)),
    }

    # Period
    period = {}
    if visit.check_in_time:
        period['start'] = visit.check_in_time.isoformat()
    if visit.check_out_time:
        period['end'] = visit.check_out_time.isoformat()
    if period:
        resource['period'] = period

    # Khoa xác nhận
    if visit.confirmed_department:
        resource['serviceProvider'] = {
            'display': str(visit.confirmed_department),
        }

    # Reason (chief complaint)
    if visit.chief_complaint:
        resource['reasonCode'] = [{
            'text': visit.chief_complaint,
        }]

    # Priority
    if visit.priority == 'EMERGENCY':
        resource['priority'] = build_codeable_concept(
            'http://terminology.hl7.org/CodeSystem/v3-ActPriority',
            'EM', 'emergency'
        )

    return resource


# ═══════════════════════════════════════════════════════════════════════════════
# CLINICAL RECORD → FHIR Condition
# ═══════════════════════════════════════════════════════════════════════════════

def map_clinical_record_to_condition(record) -> dict:
    """
    Map ClinicalRecord → FHIR R4 Condition resource.
    Focuses on the primary diagnosis (main_icd).

    Args:
        record: apps.medical_services.emr.models.ClinicalRecord instance

    Returns:
        dict: FHIR Condition resource
    """
    resource = {
        'resourceType': RESOURCE_CONDITION,
        'id': str(record.id),
        'subject': build_reference(RESOURCE_PATIENT, str(record.visit.patient_id)),
        'encounter': build_reference(RESOURCE_ENCOUNTER, str(record.visit_id)),
        'clinicalStatus': build_codeable_concept(
            'http://terminology.hl7.org/CodeSystem/condition-clinical',
            'active', 'Active'
        ),
    }

    # ICD-10 chính
    if record.main_icd:
        resource['code'] = build_codeable_concept(
            SYSTEM_ICD10,
            record.main_icd.code,
            record.main_icd.name,
            text=record.final_diagnosis or ''
        )
    elif record.final_diagnosis:
        resource['code'] = {'text': record.final_diagnosis}

    # Chief complaint as note
    if record.chief_complaint:
        resource['note'] = [{'text': record.chief_complaint}]

    # Verification status
    if record.is_finalized:
        resource['verificationStatus'] = build_codeable_concept(
            'http://terminology.hl7.org/CodeSystem/condition-ver-status',
            'confirmed', 'Confirmed'
        )
    else:
        resource['verificationStatus'] = build_codeable_concept(
            'http://terminology.hl7.org/CodeSystem/condition-ver-status',
            'provisional', 'Provisional'
        )

    return resource


# ═══════════════════════════════════════════════════════════════════════════════
# VITAL SIGNS → FHIR Observation (multiple)
# ═══════════════════════════════════════════════════════════════════════════════

def map_vital_signs_to_observations(visit) -> list[dict]:
    """
    Map Visit.vital_signs JSON → list of FHIR R4 Observation resources.

    Args:
        visit: Visit instance with vital_signs JSONField

    Returns:
        list[dict]: List of FHIR Observation resources
    """
    if not visit.vital_signs:
        return []

    observations = []
    patient_ref = build_reference(RESOURCE_PATIENT, str(visit.patient_id))
    encounter_ref = build_reference(RESOURCE_ENCOUNTER, str(visit.id))

    for key, value in visit.vital_signs.items():
        if value is None:
            continue

        loinc_info = VITAL_SIGN_LOINC.get(key)
        if not loinc_info:
            continue

        obs = {
            'resourceType': RESOURCE_OBSERVATION,
            'id': f'{visit.id}-vs-{key}',
            'status': 'final',
            'category': [build_codeable_concept(
                'http://terminology.hl7.org/CodeSystem/observation-category',
                'vital-signs', 'Vital Signs'
            )],
            'code': build_codeable_concept(
                SYSTEM_LOINC,
                loinc_info['code'],
                loinc_info['display'],
            ),
            'subject': patient_ref,
            'encounter': encounter_ref,
            'valueQuantity': {
                'value': float(value),
                'unit': loinc_info['unit'],
                'system': 'http://unitsofmeasure.org',
                'code': loinc_info['unit'],
            },
        }

        if visit.check_in_time:
            obs['effectiveDateTime'] = visit.check_in_time.isoformat()

        observations.append(obs)

    return observations


# ═══════════════════════════════════════════════════════════════════════════════
# LAB RESULTS → FHIR DiagnosticReport + Observations
# ═══════════════════════════════════════════════════════════════════════════════

def map_lab_order_to_diagnostic_report(lab_order) -> dict:
    """
    Map LabOrder → FHIR R4 DiagnosticReport + embedded Observation results.

    Args:
        lab_order: apps.medical_services.lis.models.LabOrder instance
                   (prefetch `details__result`, `details__test` recommended)

    Returns:
        dict: FHIR DiagnosticReport resource with contained Observations
    """
    resource = {
        'resourceType': RESOURCE_DIAGNOSTIC_REPORT,
        'id': str(lab_order.id),
        'status': DIAGNOSTIC_REPORT_STATUS_MAP.get(lab_order.status, 'unknown'),
        'category': [build_codeable_concept(
            'http://terminology.hl7.org/CodeSystem/v2-0074',
            'LAB', 'Laboratory'
        )],
        'code': {'text': f'Lab Order #{lab_order.id}'},
        'subject': build_reference(RESOURCE_PATIENT, str(lab_order.patient_id)),
        'encounter': build_reference(RESOURCE_ENCOUNTER, str(lab_order.visit_id)),
    }

    if lab_order.created_at:
        resource['issued'] = lab_order.created_at.isoformat()

    # Embed individual test results as Observations
    contained_obs = []
    result_refs = []

    for detail in lab_order.details.all():
        obs = _map_lab_detail_to_observation(detail, lab_order)
        if obs:
            contained_obs.append(obs)
            result_refs.append({'reference': f'#{obs["id"]}'})

    if contained_obs:
        resource['contained'] = contained_obs
        resource['result'] = result_refs

    return resource


def _map_lab_detail_to_observation(detail, lab_order) -> Optional[dict]:
    """Map a single LabOrderDetail (+ LabResult) to FHIR Observation."""
    test = detail.test

    obs = {
        'resourceType': RESOURCE_OBSERVATION,
        'id': f'obs-{detail.id}',
        'status': 'final' if hasattr(detail, 'result') else 'registered',
        'code': build_codeable_concept(
            'urn:oid:his-aio:lab-test',
            test.code,
            test.name,
        ),
        'subject': build_reference(RESOURCE_PATIENT, str(lab_order.patient_id)),
    }

    # Kết quả thực tế
    if hasattr(detail, 'result') and detail.result:
        result = detail.result

        if result.value_numeric is not None:
            obs['valueQuantity'] = {
                'value': float(result.value_numeric),
                'unit': test.unit or '',
            }
        elif result.value_string:
            obs['valueString'] = result.value_string

        # Reference range (LabTest.min_limit / max_limit)
        if test.min_limit is not None or test.max_limit is not None:
            ref_range = {}
            if test.min_limit is not None:
                ref_range['low'] = {'value': float(test.min_limit), 'unit': test.unit or ''}
            if test.max_limit is not None:
                ref_range['high'] = {'value': float(test.max_limit), 'unit': test.unit or ''}
            obs['referenceRange'] = [ref_range]

        # Abnormal flag
        if result.is_abnormal:
            obs['interpretation'] = [build_codeable_concept(
                'http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation',
                result.abnormal_flag or 'A',
                'Abnormal',
            )]

    return obs


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGING → FHIR ImagingStudy
# ═══════════════════════════════════════════════════════════════════════════════

def map_imaging_order_to_study(imaging_order) -> dict:
    """
    Map ImagingOrder → FHIR R4 ImagingStudy resource.

    Args:
        imaging_order: apps.medical_services.ris.models.ImagingOrder instance
                       (select_related `procedure__modality`, `execution`, `result`)

    Returns:
        dict: FHIR ImagingStudy resource
    """
    procedure = imaging_order.procedure
    modality = procedure.modality if procedure else None
    modality_code = modality.code if modality else 'OT'  # OT = Other

    resource = {
        'resourceType': RESOURCE_IMAGING_STUDY,
        'id': str(imaging_order.id),
        'status': _map_imaging_status(imaging_order.status),
        'subject': build_reference(RESOURCE_PATIENT, str(imaging_order.patient_id)),
        'encounter': build_reference(RESOURCE_ENCOUNTER, str(imaging_order.visit_id)),
        'modality': [
            MODALITY_MAP.get(modality_code, {
                'system': 'http://dicom.nema.org/resources/ontology/DCM',
                'code': modality_code,
                'display': modality_code,
            })
        ],
        'description': str(procedure) if procedure else '',
    }

    if imaging_order.order_time:
        resource['started'] = imaging_order.order_time.isoformat()

    # Execution info
    if hasattr(imaging_order, 'execution') and imaging_order.execution:
        execution = imaging_order.execution

        # DICOM Study UID (nếu có từ PACS)
        if hasattr(execution, 'study_instance_uid') and execution.study_instance_uid:
            resource['identifier'] = [
                build_identifier(SYSTEM_DICOM_UID, execution.study_instance_uid)
            ]

        # Series info
        series = {
            'uid': f'urn:oid:his-aio:series:{imaging_order.id}',
            'modality': MODALITY_MAP.get(modality_code, {
                'system': 'http://dicom.nema.org/resources/ontology/DCM',
                'code': modality_code,
            }),
        }

        # Preview image as instance endpoint
        if execution.preview_image_url:
            series['instance'] = [{
                'uid': f'urn:oid:his-aio:instance:{imaging_order.id}',
                'sopClass': {
                    'system': 'urn:ietf:rfc:3986',
                    'code': '1.2.840.10008.5.1.4.1.1.2',  # CT Image Storage
                },
            }]
            series['endpoint'] = [{
                'reference': execution.preview_image_url,
            }]

        resource['series'] = [series]

    # Result/Report
    if hasattr(imaging_order, 'result') and imaging_order.result:
        result = imaging_order.result
        if result.conclusion:
            resource['description'] = result.conclusion

    return resource


def _map_imaging_status(status: str) -> str:
    """Map ImagingOrder.Status → FHIR ImagingStudy.status."""
    status_map = {
        'PENDING': 'registered',
        'SCHEDULED': 'registered',
        'IN_PROGRESS': 'available',
        'COMPLETED': 'available',
        'REPORTED': 'available',
        'VERIFIED': 'available',
        'CANCELLED': 'cancelled',
    }
    return status_map.get(status, 'unknown')


# ═══════════════════════════════════════════════════════════════════════════════
# BUNDLE — Tổng hợp toàn bộ dữ liệu bệnh nhân
# ═══════════════════════════════════════════════════════════════════════════════

def build_patient_bundle(patient, visits=None) -> dict:
    """
    Build a FHIR Bundle containing all resources for one patient.

    Args:
        patient: Patient instance
        visits: Optional queryset of Visit instances (with related data prefetched)

    Returns:
        dict: FHIR Bundle resource
    """
    entries = []

    # Patient
    patient_resource = map_patient_to_fhir(patient)
    entries.append(_bundle_entry(patient_resource))

    if visits is None:
        visits = patient.visits.all().select_related(
            'confirmed_department',
        ).prefetch_related(
            'clinical_record',
            'lab_orders__details__test',
            'lab_orders__details__result',
            'imaging_orders__procedure__modality',
            'imaging_orders__execution',
            'imaging_orders__result',
        )

    for visit in visits:
        # Encounter
        encounter = map_visit_to_encounter(visit)
        entries.append(_bundle_entry(encounter))

        # Vital signs
        for obs in map_vital_signs_to_observations(visit):
            entries.append(_bundle_entry(obs))

        # Clinical Record → Condition
        if hasattr(visit, 'clinical_record'):
            condition = map_clinical_record_to_condition(visit.clinical_record)
            entries.append(_bundle_entry(condition))

        # Lab Orders → DiagnosticReports
        for lab_order in visit.lab_orders.all():
            report = map_lab_order_to_diagnostic_report(lab_order)
            entries.append(_bundle_entry(report))

        # Imaging Orders → ImagingStudy
        for imaging_order in visit.imaging_orders.all():
            study = map_imaging_order_to_study(imaging_order)
            entries.append(_bundle_entry(study))

    return {
        'resourceType': RESOURCE_BUNDLE,
        'type': 'collection',
        'total': len(entries),
        'entry': entries,
    }


def _bundle_entry(resource: dict) -> dict:
    """Wrap a FHIR resource in a Bundle entry."""
    resource_type = resource.get('resourceType', '')
    resource_id = resource.get('id', '')
    return {
        'fullUrl': f'urn:uuid:{resource_id}',
        'resource': resource,
        'request': {
            'method': 'PUT',
            'url': f'{resource_type}/{resource_id}',
        },
    }
