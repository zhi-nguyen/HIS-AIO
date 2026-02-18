"""
Kiosk Services — Business logic cho Kiosk tự phục vụ

Layer 1: identify_patient() — Xác thực qua QR CCCD/BHYT
Layer 2: check_active_visit() — Chặn lượt khám trùng trong ngày
"""

import re
import copy
import logging
import threading
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone
from django.db import transaction

from apps.core_services.patients.models import Patient
from apps.core_services.reception.models import Visit
from apps.core_services.qms.models import ServiceStation, StationType
from apps.core_services.qms.services import ClinicalQueueService, QueueService
from apps.core_services.insurance_mock.mock_data import (
    LOOKUP_BY_CCCD, LOOKUP_BY_SHORT_CODE, LOOKUP_BY_FULL_CODE
)

logger = logging.getLogger(__name__)

# ==============================================================================
# REGEX PATTERNS (reuse từ insurance_mock)
# ==============================================================================
PATTERN_CCCD = re.compile(r'^\d{12}$')
PATTERN_INSURANCE_SHORT = re.compile(r'^\d{10}$')
PATTERN_INSURANCE_FULL = re.compile(r'^[A-Za-z]{2}\d{13}$')


# ==============================================================================
# CUSTOM EXCEPTIONS
# ==============================================================================
class ActiveVisitExistsError(Exception):
    """Bệnh nhân đã có lượt khám chưa hoàn thành trong ngày."""
    def __init__(self, visit):
        self.visit = visit
        super().__init__(
            f"Bạn đang có một lượt khám chưa hoàn thành (Mã: {visit.visit_code}). "
            f"Vui lòng kiểm tra lại."
        )


class PatientNotFoundError(Exception):
    """Không tìm thấy bệnh nhân."""
    pass


class InvalidScanDataError(Exception):
    """Dữ liệu quét không hợp lệ."""
    pass


# ==============================================================================
# KIOSK SERVICE
# ==============================================================================
class KioskService:
    """
    Service chính cho Kiosk tự phục vụ.
    
    Flow:
    1. identify_patient(scan_data) → {patient, insurance_info, is_new_patient}
    2. register_visit(patient_id, chief_complaint) → {visit, queue_number, ...}
    """

    # ------------------------------------------------------------------
    # LAYER 1: Identify Patient (Hardware QR/Chip Reader)
    # ------------------------------------------------------------------
    @staticmethod
    def _classify_scan_data(scan_data: str) -> str:
        """
        Phân loại dữ liệu quét.
        Returns: 'cccd' | 'insurance_short' | 'insurance_full' | 'invalid'
        """
        q = scan_data.strip()
        if PATTERN_CCCD.match(q):
            return 'cccd'
        if PATTERN_INSURANCE_SHORT.match(q):
            return 'insurance_short'
        if PATTERN_INSURANCE_FULL.match(q):
            return 'insurance_full'
        return 'invalid'

    @staticmethod
    def _lookup_insurance(scan_data: str, scan_type: str) -> dict | None:
        """
        Tra cứu thông tin BHYT từ mock data.
        Returns: dict insurance data hoặc None nếu không tìm thấy.
        """
        if scan_type == 'cccd':
            record = LOOKUP_BY_CCCD.get(scan_data)
        elif scan_type == 'insurance_short':
            record = LOOKUP_BY_SHORT_CODE.get(scan_data)
        elif scan_type == 'insurance_full':
            record = LOOKUP_BY_FULL_CODE.get(scan_data.upper())
        else:
            return None
        
        return copy.deepcopy(record) if record else None

    @staticmethod
    def _find_or_create_patient(scan_data: str, scan_type: str, insurance_info: dict | None) -> tuple:
        """
        Tìm hoặc tạo Patient từ dữ liệu quét.
        
        Returns: (patient, is_new_patient)
        """
        # --- Tìm theo CCCD ---
        if scan_type == 'cccd':
            try:
                patient = Patient.objects.get(id_card=scan_data)
                return patient, False
            except Patient.DoesNotExist:
                pass

        # --- Tìm theo mã BHYT ---
        if scan_type in ('insurance_short', 'insurance_full'):
            insurance_code = scan_data if scan_type == 'insurance_full' else None
            
            # Thử tìm theo insurance_number
            if insurance_code:
                try:
                    patient = Patient.objects.get(insurance_number=insurance_code)
                    return patient, False
                except Patient.DoesNotExist:
                    pass

        # --- Nếu có insurance_info, tìm theo CCCD trong mock data ---
        if insurance_info:
            # Tìm CCCD tương ứng trong mock data
            from apps.core_services.insurance_mock.mock_data import MOCK_RECORDS
            for record in MOCK_RECORDS:
                if record.get('data', {}).get('insurance_code') == insurance_info.get('insurance_code'):
                    cccd = record.get('cccd')
                    if cccd:
                        try:
                            patient = Patient.objects.get(id_card=cccd)
                            return patient, False
                        except Patient.DoesNotExist:
                            break

        # --- Tạo Patient mới nếu có insurance_info ---
        if insurance_info:
            # Parse tên
            full_name = insurance_info.get('patient_name', 'UNKNOWN')
            name_parts = full_name.split()
            first_name = name_parts[-1] if name_parts else 'Unknown'
            last_name = ' '.join(name_parts[:-1]) if len(name_parts) > 1 else ''
            
            # Parse giới tính
            gender_map = {'male': 'M', 'female': 'F'}
            gender = gender_map.get(insurance_info.get('gender', ''), 'O')
            
            # Parse ngày sinh
            dob = None
            dob_str = insurance_info.get('dob')
            if dob_str:
                try:
                    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Tìm CCCD cho patient mới
            id_card = scan_data if scan_type == 'cccd' else None
            if not id_card:
                from apps.core_services.insurance_mock.mock_data import MOCK_RECORDS
                for record in MOCK_RECORDS:
                    if record.get('data', {}).get('insurance_code') == insurance_info.get('insurance_code'):
                        id_card = record.get('cccd')
                        break
            
            # Generate patient_code
            today_str = timezone.now().strftime('%Y%m%d')
            count = Patient.objects.filter(created_at__date=timezone.now().date()).count() + 1
            patient_code = f"BN-{today_str}-{count:04d}"
            
            patient = Patient.objects.create(
                patient_code=patient_code,
                id_card=id_card,
                insurance_number=insurance_info.get('insurance_code'),
                first_name=first_name,
                last_name=last_name,
                date_of_birth=dob,
                gender=gender,
            )
            
            logger.info(f"[KIOSK] Tạo Patient mới: {patient.patient_code} - {patient.full_name}")
            return patient, True
        
        # --- Không có insurance info → không thể tạo ---
        raise PatientNotFoundError(
            "Không tìm thấy thông tin bệnh nhân. "
            "Vui lòng liên hệ quầy tiếp đón để được hỗ trợ."
        )

    @classmethod
    def identify_patient(cls, scan_data: str) -> dict:
        """
        Layer 1: Xác thực bệnh nhân qua dữ liệu quét QR.
        
        Args:
            scan_data: Dữ liệu quét từ QR CCCD (12 số) hoặc mã BHYT (10/15 ký tự)
        
        Returns:
            {
                'patient': Patient instance,
                'insurance_info': dict hoặc None,
                'is_new_patient': bool,
                'has_active_visit': bool,
                'active_visit': Visit hoặc None,
            }
        
        Raises:
            InvalidScanDataError: Dữ liệu quét không hợp lệ
            PatientNotFoundError: Không tìm thấy bệnh nhân
        """
        scan_data = scan_data.strip()
        scan_type = cls._classify_scan_data(scan_data)
        
        if scan_type == 'invalid':
            raise InvalidScanDataError(
                "Dữ liệu quét không hợp lệ. "
                "Chấp nhận: CCCD (12 số), mã BHYT mới (10 số), "
                "hoặc mã BHYT cũ (15 ký tự, VD: TE1790000000123)."
            )
        
        # Tra cứu BHYT
        insurance_info = cls._lookup_insurance(scan_data, scan_type)
        
        # Tìm hoặc tạo Patient
        patient, is_new_patient = cls._find_or_create_patient(
            scan_data, scan_type, insurance_info
        )
        
        # Check active visit
        active_visit = cls._get_active_visit(patient)
        
        logger.info(
            f"[KIOSK] Identify: {patient.patient_code} | "
            f"type={scan_type} | new={is_new_patient} | "
            f"active_visit={'YES' if active_visit else 'NO'}"
        )
        
        return {
            'patient': patient,
            'insurance_info': insurance_info,
            'is_new_patient': is_new_patient,
            'has_active_visit': active_visit is not None,
            'active_visit': active_visit,
        }

    # ------------------------------------------------------------------
    # LAYER 2: Active Visit Validation
    # ------------------------------------------------------------------
    @staticmethod
    def _get_active_visit(patient: Patient) -> Visit | None:
        """
        Tìm lượt khám chưa hoàn thành trong ngày.
        
        Statuses coi là "active" (chưa xong):
        - CHECK_IN, TRIAGE, WAITING, IN_PROGRESS, PENDING_RESULTS
        
        Statuses coi là "finished":
        - COMPLETED, CANCELLED
        """
        today = timezone.now().date()
        finished_statuses = [Visit.Status.COMPLETED, Visit.Status.CANCELLED]
        
        return Visit.objects.filter(
            patient=patient,
            created_at__date=today,
        ).exclude(
            status__in=finished_statuses
        ).order_by('-created_at').first()

    @classmethod
    def check_active_visit(cls, patient: Patient):
        """
        Layer 2: Kiểm tra lượt khám active.
        
        Raises:
            ActiveVisitExistsError: Nếu đã có lượt khám chưa hoàn thành
        """
        active_visit = cls._get_active_visit(patient)
        if active_visit:
            raise ActiveVisitExistsError(active_visit)

    # ------------------------------------------------------------------
    # REGISTER VISIT (Kết hợp Layer 1 + 2)
    # ------------------------------------------------------------------
    @classmethod
    @transaction.atomic
    def register_visit(cls, patient_id, chief_complaint: str) -> dict:
        """
        Đăng ký lượt khám từ Kiosk.
        
        Flow:
        1. Tìm Patient
        2. Check active visit (Layer 2)
        3. Gọi ClinicalQueueService.checkin_walkin() — tạo Visit + Queue trong 1 lần
        4. Cập nhật Visit.chief_complaint (để reception thấy lý do khám)
        5. Trigger AI summarize (background)
        
        ⚠️ CHÚ Ý: KHÔNG gọi ReceptionService.create_visit() riêng!
           checkin_walkin() đã gọi create_visit() bên trong rồi.
        
        Returns:
            {
                'visit': Visit,
                'queue_number': str,
                'daily_sequence': int,
                'estimated_wait_minutes': int,
                'message': str,
            }
        
        Raises:
            PatientNotFoundError: Patient không tồn tại
            ActiveVisitExistsError: Có lượt khám chưa xong
        """
        # 1. Tìm Patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise PatientNotFoundError("Không tìm thấy bệnh nhân.")
        
        # 2. Check active visit (Layer 2)
        cls.check_active_visit(patient)
        
        # 3. Tạo Visit + Queue bằng checkin_walkin (1 lần duy nhất)
        station = cls._get_default_reception_station()
        
        result = ClinicalQueueService.checkin_walkin(
            patient=patient,
            station=station,
            reason=chief_complaint,
            extra_priority=0,
        )
        
        visit = result['visit']
        
        # 4. Cập nhật Visit.chief_complaint để reception frontend thấy
        #    (ReceptionService.create_visit chỉ set ClinicalRecord.chief_complaint,
        #     nhưng TriageModal đọc từ visit.chief_complaint)
        visit.chief_complaint = chief_complaint
        visit.save(update_fields=['chief_complaint'])
        
        # 5. Ước tính thời gian chờ
        estimated_wait = QueueService.get_estimated_wait_time(station)
        
        # 6. Trigger AI summarize (background - fire-and-forget)
        cls._trigger_ai_summary_async(visit, chief_complaint)
        
        logger.info(
            f"[KIOSK] Register: {patient.patient_code} | "
            f"visit={visit.visit_code} | "
            f"queue={result['queue_number'].number_code} | "
            f"seq={result['queue_number'].daily_sequence}"
        )
        
        return {
            'visit': visit,
            'queue_number': result['queue_number'].number_code,
            'daily_sequence': result['queue_number'].daily_sequence,
            'estimated_wait_minutes': estimated_wait,
            'message': f"Đăng ký thành công! Số thứ tự của bạn: {result['queue_number'].daily_sequence}",
        }

    @staticmethod
    def _get_default_reception_station() -> ServiceStation:
        """
        Lấy station RECEPTION mặc định.
        Nếu chưa có → tạo mới.
        """
        station = ServiceStation.objects.filter(
            station_type=StationType.RECEPTION,
            is_active=True,
        ).first()
        
        if not station:
            station = ServiceStation.objects.create(
                code='KIOSK-01',
                name='Kiosk Tự Phục Vụ',
                station_type=StationType.RECEPTION,
                is_active=True,
            )
            logger.info(f"[KIOSK] Tạo ServiceStation mặc định: {station.code}")
        
        return station

    # ------------------------------------------------------------------
    # AI SUMMARY (Background Task)
    # ------------------------------------------------------------------
    @staticmethod
    def _trigger_ai_summary_async(visit: Visit, chief_complaint: str):
        """
        Gọi AI Summarize Agent trong thread riêng (fire-and-forget).
        Kết hợp lý do khám + bệnh án cũ → tóm tắt cho agent Phân Luồng.
        Không block response cho bệnh nhân.
        """
        def _run_summary():
            try:
                logger.info(f"[KIOSK] AI Summary started for visit: {visit.visit_code}")
                
                from apps.medical_services.emr.models import ClinicalRecord
                
                # Lấy thông tin bệnh nhân
                patient = visit.patient
                
                # Lấy lịch sử khám cũ
                past_visits = Visit.objects.filter(
                    patient=patient,
                    status=Visit.Status.COMPLETED,
                ).exclude(
                    id=visit.id
                ).order_by('-check_in_time')[:5]
                
                # Build context từ bệnh án cũ
                history_lines = []
                for pv in past_visits:
                    pv_complaint = pv.chief_complaint or ''
                    # Thử lấy thêm từ ClinicalRecord
                    if not pv_complaint:
                        try:
                            cr = ClinicalRecord.objects.get(visit=pv)
                            pv_complaint = cr.chief_complaint or 'Không rõ lý do'
                        except ClinicalRecord.DoesNotExist:
                            pv_complaint = 'Không rõ lý do'
                    
                    dept = pv.confirmed_department.name if pv.confirmed_department else 'N/A'
                    date = pv.check_in_time.strftime('%d/%m/%Y') if pv.check_in_time else 'N/A'
                    history_lines.append(f"- {date}: {pv_complaint} (Khoa: {dept})")
                
                history_text = '\n'.join(history_lines) if history_lines else 'Chưa có lịch sử khám.'
                
                # Build message cho Summarize Agent
                age = ''
                if patient.date_of_birth:
                    from datetime import date as date_type
                    today = date_type.today()
                    age = today.year - patient.date_of_birth.year
                    if (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day):
                        age -= 1
                
                structured_message = (
                    f"[KIOSK_CHECKIN_SUMMARY]\n"
                    f"THÔNG TIN BỆNH NHÂN:\n"
                    f"Mã BN: {patient.patient_code}\n"
                    f"Họ tên: {patient.full_name}\n"
                    f"Tuổi: {age or 'N/A'} | Giới: {patient.gender}\n"
                    f"Ngày sinh: {patient.date_of_birth or 'N/A'}\n\n"
                    f"LÝ DO KHÁM HÔM NAY:\n{chief_complaint}\n\n"
                    f"LỊCH SỬ KHÁM GẦN ĐÂY:\n{history_text}\n\n"
                    f"YÊU CẦU: Tóm tắt thông tin bệnh nhân, kết hợp lý do khám hôm nay "
                    f"với bệnh án cũ. Đưa ra các chỉ số cần lưu ý khi đo sinh hiệu "
                    f"và gợi ý cho agent Phân Luồng."
                )
                
                # Gọi summarize_node trực tiếp
                from langchain_core.messages import HumanMessage
                from apps.ai_engine.agents.summarize_agent.node import summarize_node
                
                state = {
                    "messages": [HumanMessage(content=structured_message)],
                    "current_agent": "summarize",
                }
                
                result = summarize_node(state)
                
                # Lấy kết quả từ AI
                ai_messages = result.get("messages", [])
                if ai_messages:
                    ai_content = ai_messages[0].content
                    # Lưu vào Visit.triage_ai_response để reception / triage agent thấy
                    visit.refresh_from_db()
                    visit.triage_ai_response = ai_content
                    visit.save(update_fields=['triage_ai_response'])
                    logger.info(f"[KIOSK] AI Summary completed for visit: {visit.visit_code}")
                else:
                    logger.warning(f"[KIOSK] AI Summary returned empty for visit: {visit.visit_code}")
                
            except Exception as e:
                logger.error(f"[KIOSK] AI Summary error for visit {visit.visit_code}: {e}")
                # Fallback: lưu text đơn giản nếu AI fail
                try:
                    visit.refresh_from_db()
                    visit.triage_ai_response = (
                        f"[Tóm tắt tự động - Kiosk]\n"
                        f"Lý do khám: {chief_complaint}\n"
                        f"(AI tóm tắt không khả dụng, vui lòng xem chi tiết tại quầy.)"
                    )
                    visit.save(update_fields=['triage_ai_response'])
                except Exception:
                    pass
        
        thread = threading.Thread(target=_run_summary, daemon=True)
        thread.start()
