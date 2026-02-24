"""
Modality Worklist (MWL) — tạo worklist entries cho thiết bị chẩn đoán hình ảnh.

Khi có ImagingOrder ở trạng thái PENDING/SCHEDULED, hệ thống tạo MWL entry
để thiết bị chụp (CT, MRI, X-Ray...) tự động nhận thông tin bệnh nhân.

Worklist entries tuân theo chuẩn DICOM MWL (C-FIND),
nhưng đây là dạng JSON để serve qua REST API.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def generate_worklist_entries(
    modality_code: Optional[str] = None,
    ae_title: Optional[str] = None,
    date_from: Optional[datetime] = None,
) -> list[dict]:
    """
    Tạo danh sách MWL entries từ ImagingOrder đang chờ thực hiện.

    Args:
        modality_code: Lọc theo loại máy (CT, MR, US...)
        ae_title: Lọc theo AE Title của máy
        date_from: Chỉ lấy orders từ thời điểm này

    Returns:
        list[dict]: Worklist entries theo format DICOM MWL
    """
    from apps.medical_services.ris.models import ImagingOrder

    queryset = ImagingOrder.objects.filter(
        status__in=['PENDING', 'SCHEDULED'],
    ).select_related(
        'patient', 'visit', 'procedure__modality',
    ).order_by('priority', 'order_time')

    if modality_code:
        queryset = queryset.filter(procedure__modality__code=modality_code)

    if date_from:
        queryset = queryset.filter(order_time__gte=date_from)

    entries = []
    for order in queryset:
        entry = _build_worklist_entry(order)
        if entry:
            entries.append(entry)

    logger.info(f"Generated {len(entries)} MWL entries (modality={modality_code})")
    return entries


def _build_worklist_entry(order) -> Optional[dict]:
    """
    Build a single worklist entry from an ImagingOrder.

    Format theo DICOM MWL tags (JSON representation).
    """
    patient = order.patient
    procedure = order.procedure
    modality = procedure.modality if procedure else None

    if not patient or not procedure:
        return None

    entry = {
        # ─── Patient Identification ───
        'PatientName': f'{patient.last_name}^{patient.first_name}',
        'PatientID': patient.patient_code,
        'PatientBirthDate': (
            patient.date_of_birth.strftime('%Y%m%d')
            if patient.date_of_birth else ''
        ),
        'PatientSex': _dicom_sex(patient.gender),

        # ─── Visit Identification ───
        'AccessionNumber': str(order.id)[:16],  # Max 16 chars
        'ReferringPhysicianName': '',

        # ─── Requested Procedure ───
        'RequestedProcedureDescription': str(procedure),
        'RequestedProcedureID': str(order.id)[:16],
        'RequestedProcedurePriority': _dicom_priority(order.priority),

        # ─── Scheduled Procedure Step ───
        'ScheduledProcedureStepSequence': [{
            'Modality': modality.code if modality else 'OT',
            'ScheduledStationAETitle': '',
            'ScheduledProcedureStepStartDate': (
                order.order_time.strftime('%Y%m%d')
                if order.order_time else ''
            ),
            'ScheduledProcedureStepStartTime': (
                order.order_time.strftime('%H%M%S')
                if order.order_time else ''
            ),
            'ScheduledPerformingPhysicianName': '',
            'ScheduledProcedureStepDescription': str(procedure),
            'ScheduledProcedureStepID': str(order.id)[:16],
        }],

        # ─── Study Instance UID (placeholder until assigned by modality) ───
        'StudyInstanceUID': '',

        # ─── Additional info ───
        '_order_id': str(order.id),
        '_visit_code': order.visit.visit_code if order.visit else '',
        '_note': order.note or '',
        '_priority_display': order.get_priority_display() if hasattr(order, 'get_priority_display') else '',
    }

    return entry


def _dicom_sex(gender: str) -> str:
    """Map internal gender → DICOM Patient Sex."""
    return {'M': 'M', 'F': 'F'}.get(gender, 'O')


def _dicom_priority(priority: str) -> str:
    """Map ImagingOrder.Priority → DICOM Requested Procedure Priority."""
    return {
        'NORMAL': 'LOW',
        'URGENT': 'HIGH',
        'STAT': 'STAT',
    }.get(priority, 'LOW')
