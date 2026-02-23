"""
FHIR R4 Resource type constants and helper utilities.
Defines supported resource types and common FHIR value sets used by mappers.
"""

# ─── FHIR R4 Resource Types (supported by this HIS) ─────────────────────────

RESOURCE_PATIENT = 'Patient'
RESOURCE_ENCOUNTER = 'Encounter'
RESOURCE_CONDITION = 'Condition'
RESOURCE_OBSERVATION = 'Observation'
RESOURCE_DIAGNOSTIC_REPORT = 'DiagnosticReport'
RESOURCE_IMAGING_STUDY = 'ImagingStudy'
RESOURCE_BUNDLE = 'Bundle'

SUPPORTED_RESOURCES = [
    RESOURCE_PATIENT,
    RESOURCE_ENCOUNTER,
    RESOURCE_CONDITION,
    RESOURCE_OBSERVATION,
    RESOURCE_DIAGNOSTIC_REPORT,
    RESOURCE_IMAGING_STUDY,
]

# ─── Identifier Systems ─────────────────────────────────────────────────────

# Hệ thống định danh dùng trong FHIR identifiers
SYSTEM_PATIENT_CODE = 'urn:oid:his-aio:patient-code'
SYSTEM_VISIT_CODE = 'urn:oid:his-aio:visit-code'
SYSTEM_CCCD = 'urn:oid:vn:cccd'                    # Căn cước công dân
SYSTEM_BHYT = 'urn:oid:vn:bhyt'                    # Bảo hiểm y tế
SYSTEM_ICD10 = 'http://hl7.org/fhir/sid/icd-10'   # ICD-10 coding system
SYSTEM_LOINC = 'http://loinc.org'                  # LOINC (Lab codes)
SYSTEM_DICOM_UID = 'urn:dicom:uid'                 # DICOM Study/Series UIDs

# ─── FHIR Value Set Mappings ────────────────────────────────────────────────

# Patient.gender  (internal → FHIR)
GENDER_MAP = {
    'M': 'male',
    'F': 'female',
    'O': 'other',
}

# Encounter.status  (Visit.Status → FHIR)
ENCOUNTER_STATUS_MAP = {
    'CHECK_IN': 'arrived',
    'TRIAGE': 'triaged',
    'WAITING': 'arrived',
    'IN_PROGRESS': 'in-progress',
    'PENDING_RESULTS': 'in-progress',
    'COMPLETED': 'finished',
    'CANCELLED': 'cancelled',
}

# Encounter.class  (Visit.Priority → FHIR)
ENCOUNTER_CLASS_MAP = {
    'NORMAL': {'code': 'AMB', 'display': 'ambulatory'},
    'ONLINE_BOOKING': {'code': 'AMB', 'display': 'ambulatory'},
    'PRIORITY': {'code': 'AMB', 'display': 'ambulatory'},
    'EMERGENCY': {'code': 'EMER', 'display': 'emergency'},
}

# DiagnosticReport.status  (LabOrder.Status / ImagingOrder.Status → FHIR)
DIAGNOSTIC_REPORT_STATUS_MAP = {
    'PENDING': 'registered',
    'SAMPLING': 'registered',
    'PROCESSING': 'preliminary',
    'COMPLETED': 'final',
    'CANCELLED': 'cancelled',
    # RIS-specific
    'SCHEDULED': 'registered',
    'IN_PROGRESS': 'preliminary',
    'REPORTED': 'final',
    'VERIFIED': 'amended',
}

# Observation category for vital signs
VITAL_SIGN_LOINC = {
    'heart_rate': {'code': '8867-4', 'display': 'Heart rate', 'unit': '/min'},
    'blood_pressure_systolic': {'code': '8480-6', 'display': 'Systolic BP', 'unit': 'mmHg'},
    'blood_pressure_diastolic': {'code': '8462-4', 'display': 'Diastolic BP', 'unit': 'mmHg'},
    'temperature': {'code': '8310-5', 'display': 'Body temperature', 'unit': 'Cel'},
    'respiratory_rate': {'code': '9279-1', 'display': 'Respiratory rate', 'unit': '/min'},
    'spo2': {'code': '2708-6', 'display': 'Oxygen saturation', 'unit': '%'},
    'weight': {'code': '29463-7', 'display': 'Body weight', 'unit': 'kg'},
    'height': {'code': '8302-2', 'display': 'Body height', 'unit': 'cm'},
}

# Modality DICOM code → FHIR ImagingStudy.modality
MODALITY_MAP = {
    'CR': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': 'CR', 'display': 'Computed Radiography'},
    'CT': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': 'CT', 'display': 'Computed Tomography'},
    'MR': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': 'MR', 'display': 'Magnetic Resonance'},
    'US': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': 'US', 'display': 'Ultrasound'},
    'DX': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': 'DX', 'display': 'Digital Radiography'},
    'XA': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': 'XA', 'display': 'X-Ray Angiography'},
    'MG': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': 'MG', 'display': 'Mammography'},
    'NM': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': 'NM', 'display': 'Nuclear Medicine'},
    'PT': {'system': 'http://dicom.nema.org/resources/ontology/DCM', 'code': 'PT', 'display': 'Positron Emission Tomography'},
}


def build_reference(resource_type: str, resource_id: str) -> dict:
    """Build a FHIR Reference object."""
    return {
        'reference': f'{resource_type}/{resource_id}',
    }


def build_identifier(system: str, value: str) -> dict:
    """Build a FHIR Identifier object."""
    return {
        'system': system,
        'value': str(value),
    }


def build_coding(system: str, code: str, display: str = '') -> dict:
    """Build a FHIR Coding object."""
    coding = {'system': system, 'code': code}
    if display:
        coding['display'] = display
    return coding


def build_codeable_concept(system: str, code: str, display: str = '', text: str = '') -> dict:
    """Build a FHIR CodeableConcept object."""
    cc = {'coding': [build_coding(system, code, display)]}
    if text:
        cc['text'] = text
    return cc
