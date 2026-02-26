"""
QMS Services - Business logic for Queue Management System
"""
from datetime import date
from django.utils import timezone
from django.db import transaction
from django.db.models import Max

from .models import ServiceStation, QueueNumber, QueueEntry, QueueStatus, QueueSourceType, StationType


class QueueService:
    """Service class for queue management operations"""
    
    @staticmethod
    def generate_queue_number(visit, station: ServiceStation) -> QueueNumber:
        """
        Tạo số thứ tự mới cho bệnh nhân tại một điểm dịch vụ.
        
        Format: {station_code}-{YYYYMMDD}-{sequence:03d}
        VD: PK01-20260131-005
        """
        today = date.today()
        date_str = today.strftime('%Y%m%d')
        
        with transaction.atomic():
            # Lấy số thứ tự lớn nhất trong ngày cho station này
            max_seq = QueueNumber.objects.filter(
                station=station,
                created_date=today
            ).aggregate(max_seq=Max('daily_sequence'))['max_seq']
            
            next_seq = (max_seq or 0) + 1
            
            # Tạo mã số thứ tự
            number_code = f"{station.code}-{date_str}-{next_seq:03d}"
            
            queue_number = QueueNumber.objects.create(
                number_code=number_code,
                daily_sequence=next_seq,
                visit=visit,
                station=station,
                created_date=today
            )
            
            return queue_number
    
    @staticmethod
    def add_to_queue(visit, station: ServiceStation, priority: int = 0) -> QueueEntry:
        """
        Thêm bệnh nhân vào hàng đợi tại một điểm dịch vụ.
        Tự động tạo số thứ tự nếu chưa có.
        """
        # Sinh số thứ tự
        queue_number = QueueService.generate_queue_number(visit, station)
        
        # Điều chỉnh priority dựa trên Visit.priority
        if hasattr(visit, 'priority'):
            if visit.priority == 'EMERGENCY':
                priority = max(priority, 10)
            elif visit.priority == 'PRIORITY':
                priority = max(priority, 5)
        
        # Tạo entry trong hàng đợi
        entry = QueueEntry.objects.create(
            queue_number=queue_number,
            station=station,
            status=QueueStatus.WAITING,
            priority=priority
        )
        
        return entry
    
    @staticmethod
    def call_next_patient(station: ServiceStation) -> QueueEntry | None:
        """
        Gọi bệnh nhân tiếp theo trong hàng đợi.
        Trả về QueueEntry đã được cập nhật hoặc None nếu hàng đợi trống.
        """
        # Tìm entry đang chờ có priority cao nhất và vào sớm nhất
        next_entry = QueueEntry.objects.filter(
            station=station,
            status=QueueStatus.WAITING
        ).order_by('-priority', 'entered_queue_time').first()
        
        if next_entry:
            next_entry.status = QueueStatus.CALLED
            next_entry.called_time = timezone.now()
            next_entry.save()
        
        return next_entry
    
    @staticmethod
    def start_service(entry: QueueEntry) -> QueueEntry:
        """
        Bắt đầu phục vụ bệnh nhân (sau khi gọi và bệnh nhân đến).
        """
        entry.status = QueueStatus.IN_PROGRESS
        entry.start_time = timezone.now()
        entry.save()
        return entry
    
    @staticmethod
    def complete_service(entry: QueueEntry) -> QueueEntry:
        """
        Hoàn thành phục vụ bệnh nhân tại điểm dịch vụ.
        """
        entry.status = QueueStatus.COMPLETED
        entry.end_time = timezone.now()
        entry.save()
        return entry
    
    @staticmethod
    def skip_patient(entry: QueueEntry, reason: str = None) -> QueueEntry:
        """
        Bỏ qua bệnh nhân (không có mặt hoặc lý do khác).
        """
        entry.status = QueueStatus.SKIPPED
        entry.end_time = timezone.now()
        if reason:
            entry.note = reason
        entry.save()
        return entry
    
    @staticmethod
    def transfer_to_station(visit, new_station: ServiceStation, priority: int = 0) -> QueueEntry:
        """
        Chuyển bệnh nhân sang điểm dịch vụ mới.
        VD: Sau khi khám xong, bác sĩ chỉ định xét nghiệm -> chuyển sang phòng lấy mẫu.
        """
        return QueueService.add_to_queue(visit, new_station, priority)
    
    @staticmethod
    def get_queue_length(station: ServiceStation) -> int:
        """
        Lấy số lượng bệnh nhân đang chờ tại một điểm dịch vụ.
        """
        return QueueEntry.objects.filter(
            station=station,
            status=QueueStatus.WAITING
        ).count()
    
    @staticmethod
    def get_waiting_list(station: ServiceStation) -> list:
        """
        Lấy danh sách bệnh nhân đang chờ tại một điểm dịch vụ.
        """
        entries = QueueEntry.objects.filter(
            station=station,
            status=QueueStatus.WAITING
        ).order_by('-priority', 'entered_queue_time').select_related(
            'queue_number', 
            'queue_number__visit',
            'queue_number__visit__patient'
        )
        return list(entries)
    
    @staticmethod
    def get_estimated_wait_time(station: ServiceStation, avg_service_time_minutes: int = 10) -> int:
        """
        Ước tính thời gian chờ (phút) dựa trên số người đang chờ.
        
        Args:
            station: Điểm dịch vụ
            avg_service_time_minutes: Thời gian phục vụ trung bình mỗi bệnh nhân (phút)
        
        Returns:
            Thời gian chờ ước tính (phút)
        """
        queue_length = QueueService.get_queue_length(station)
        return queue_length * avg_service_time_minutes
    
    @staticmethod
    def get_all_stations_status() -> list:
        """
        Lấy tình trạng tất cả các điểm dịch vụ đang hoạt động.
        """
        stations = ServiceStation.objects.filter(is_active=True)
        result = []
        
        for station in stations:
            waiting_count = QueueService.get_queue_length(station)
            in_progress = QueueEntry.objects.filter(
                station=station,
                status=QueueStatus.IN_PROGRESS
            ).first()
            
            result.append({
                'station': station,
                'waiting_count': waiting_count,
                'estimated_wait_minutes': QueueService.get_estimated_wait_time(station),
                'current_patient': in_progress.queue_number.number_code if in_progress else None
            })
        
        return result


class ClinicalQueueService:
    """
    Thuật toán Hàng chờ Lâm sàng 3 Luồng:
    - Emergency (priority=100): Ngắt ngang, gọi ngay
    - Online Booking (priority=7/3/0): Chèn ưu tiên theo mức trễ
    - Walk-in (priority=0): First Come First Served
    
    Nguyên tắc: "Chưa đến → Chưa có STT"
    STT chỉ sinh ra khi bệnh nhân ĐÃ CÓ MẶT (check-in).
    """

    # --- Priority Constants ---
    PRIORITY_EMERGENCY = 100
    PRIORITY_BOOKING_ON_TIME = 7    # Đúng giờ hoặc trễ ≤15 phút
    PRIORITY_BOOKING_LATE = 3       # Trễ 15-30 phút
    PRIORITY_BOOKING_EXPIRED = 0    # Trễ > 30 phút → mất ưu tiên
    PRIORITY_WALK_IN = 0
    PRIORITY_ELDERLY_CHILD_BONUS = 5

    # --- Lateness Thresholds (minutes) ---
    LATE_THRESHOLD_MILD = 15    # ≤15p: vẫn ưu tiên đầy đủ
    LATE_THRESHOLD_SEVERE = 30  # >30p: mất ưu tiên hoàn toàn

    @staticmethod
    def _evaluate_lateness(appointment, check_in_time=None):
        """
        Tính mức trễ so với khung giờ hẹn và trả về priority tương ứng.
        
        Returns:
            tuple: (priority, lateness_minutes, lateness_category)
        """
        if check_in_time is None:
            check_in_time = timezone.now()
        
        lateness = check_in_time - appointment.scheduled_time
        lateness_minutes = max(0, int(lateness.total_seconds() / 60))
        
        if lateness_minutes <= ClinicalQueueService.LATE_THRESHOLD_MILD:
            return (
                ClinicalQueueService.PRIORITY_BOOKING_ON_TIME,
                lateness_minutes,
                'ON_TIME'
            )
        elif lateness_minutes <= ClinicalQueueService.LATE_THRESHOLD_SEVERE:
            return (
                ClinicalQueueService.PRIORITY_BOOKING_LATE,
                lateness_minutes,
                'LATE'
            )
        else:
            return (
                ClinicalQueueService.PRIORITY_BOOKING_EXPIRED,
                lateness_minutes,
                'EXPIRED'
            )

    @staticmethod
    def checkin_walkin(patient, station, reason='', extra_priority=0):
        """
        Luồng 3: Vãng lai — FCFS
        
        Bệnh nhân đến trực tiếp, lấy số xếp cuối hàng.
        
        Args:
            patient: Patient instance
            station: ServiceStation cần xếp hàng
            reason: Lý do khám
            extra_priority: Bonus ưu tiên (VD: người già +5)
        
        Returns:
            dict: {visit, queue_entry, queue_number}
        """
        from apps.core_services.reception.services import ReceptionService
        
        priority = ClinicalQueueService.PRIORITY_WALK_IN + extra_priority
        
        # Tạo Visit
        visit = ReceptionService.create_visit(
            patient=patient,
            reason=reason,
            priority='NORMAL'
        )
        
        # Sinh STT & vào hàng đợi
        queue_number = QueueService.generate_queue_number(visit, station)
        entry = QueueEntry.objects.create(
            queue_number=queue_number,
            station=station,
            status=QueueStatus.WAITING,
            priority=priority,
            source_type=QueueSourceType.WALK_IN,
        )
        
        return {
            'visit': visit,
            'queue_entry': entry,
            'queue_number': queue_number,
            'priority': priority,
            'source': 'WALK_IN',
        }

    @staticmethod
    def checkin_from_booking(appointment_id, station):
        """
        Luồng 2: Đăng ký từ xa — Priority Insertion
        
        Bệnh nhân quét QR booking tại Kiosk.
        Hệ thống tính mức trễ → quyết định priority.
        
        Args:
            appointment_id: UUID of the Appointment
            station: ServiceStation 
        
        Returns:
            dict: {visit, queue_entry, queue_number, lateness_info}
        
        Raises:
            ValueError: Nếu Appointment không tồn tại hoặc đã check-in
        """
        from apps.core_services.appointments.models import Appointment
        from apps.core_services.reception.services import ReceptionService
        
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            raise ValueError(f"Không tìm thấy lịch hẹn: {appointment_id}")
        
        # Kiểm tra đã check-in chưa
        if appointment.status == Appointment.Status.CHECKED_IN:
            raise ValueError(f"Lịch hẹn {appointment.appointment_code} đã check-in rồi.")
        
        if appointment.status == Appointment.Status.CANCELLED:
            raise ValueError(f"Lịch hẹn {appointment.appointment_code} đã bị hủy.")
        
        check_in_time = timezone.now()
        
        # 1. Tính mức trễ → priority
        priority, lateness_minutes, lateness_category = (
            ClinicalQueueService._evaluate_lateness(appointment, check_in_time)
        )
        
        # 2. Xác định Visit priority level
        if lateness_category == 'EXPIRED':
            visit_priority = 'NORMAL'  # Mất ưu tiên → như vãng lai
        else:
            visit_priority = 'ONLINE_BOOKING'
        
        # 3. Tạo Visit từ Appointment
        visit = ReceptionService.create_visit(
            patient=appointment.patient,
            reason=appointment.reason_for_visit or '',
            priority=visit_priority
        )
        
        # 4. Liên kết Appointment ↔ Visit
        appointment.visit = visit
        appointment.status = Appointment.Status.CHECKED_IN
        appointment.save(update_fields=['visit', 'status'])
        
        # 5. Sinh STT & chèn vào hàng đợi
        queue_number = QueueService.generate_queue_number(visit, station)
        entry = QueueEntry.objects.create(
            queue_number=queue_number,
            station=station,
            status=QueueStatus.WAITING,
            priority=priority,
            source_type=QueueSourceType.ONLINE_BOOKING,
            booking_ref=appointment,
            note=f"Booking {appointment.appointment_code} | "
                 f"Hẹn: {appointment.scheduled_time.strftime('%H:%M')} | "
                 f"Check-in: {check_in_time.strftime('%H:%M')} | "
                 f"Trễ: {lateness_minutes}p ({lateness_category})"
        )
        
        return {
            'visit': visit,
            'queue_entry': entry,
            'queue_number': queue_number,
            'priority': priority,
            'source': 'ONLINE_BOOKING',
            'lateness_info': {
                'minutes': lateness_minutes,
                'category': lateness_category,
                'scheduled_time': appointment.scheduled_time,
                'check_in_time': check_in_time,
            }
        }

    @staticmethod
    def flag_emergency(patient, station, reason='Cấp cứu'):
        """
        Luồng 1: Cấp cứu — Interrupt
        
        Nhân viên y tế flag cấp cứu. STT được sinh và đặt priority=100.
        Khi bác sĩ bấm "Next", emergency luôn được quét trước.
        
        Args:
            patient: Patient instance
            station: ServiceStation
            reason: Lý do cấp cứu
        
        Returns:
            dict: {visit, queue_entry, queue_number}
        """
        from apps.core_services.reception.services import ReceptionService
        
        visit = ReceptionService.create_visit(
            patient=patient,
            reason=reason,
            priority='EMERGENCY'
        )
        
        queue_number = QueueService.generate_queue_number(visit, station)
        entry = QueueEntry.objects.create(
            queue_number=queue_number,
            station=station,
            status=QueueStatus.WAITING,
            priority=ClinicalQueueService.PRIORITY_EMERGENCY,
            source_type=QueueSourceType.EMERGENCY,
            note=f"🚨 CẤP CỨU: {reason}"
        )
        
        return {
            'visit': visit,
            'queue_entry': entry,
            'queue_number': queue_number,
            'priority': ClinicalQueueService.PRIORITY_EMERGENCY,
            'source': 'EMERGENCY',
        }

    # --- Max concurrent calls ---
    MAX_CONCURRENT_CALLS = 3

    @staticmethod
    def call_next_patient(station):
        """
        Bác sĩ gọi bệnh nhân tiếp theo.
        """
        import logging
        logger = logging.getLogger('qms')
        from datetime import date as date_cls

        logger.info('[CALL_NEXT] station=%s (id=%s)', station.code, station.id)

        # Bước 0: Đếm số đang active (CALLED hoặc IN_PROGRESS) hôm nay
        active_count = QueueEntry.objects.filter(
            station=station,
            status__in=[QueueStatus.CALLED, QueueStatus.IN_PROGRESS],
            entered_queue_time__date=date_cls.today(),
        ).count()

        # Bước 1: Quét Emergency — bỏ qua giới hạn
        emergency = QueueEntry.objects.filter(
            station=station,
            status=QueueStatus.WAITING,
            source_type=QueueSourceType.EMERGENCY,
        ).order_by('entered_queue_time').first()
        
        if emergency:
            emergency.status = QueueStatus.CALLED
            emergency.called_time = timezone.now()
            emergency.save(update_fields=['status', 'called_time'])
            logger.info('[CALL_NEXT] Called EMERGENCY entry=%s station_id=%s', emergency.id, emergency.station_id)
            # TTS: pre-generate for upcoming patients
            ClinicalQueueService._trigger_tts_pre_generate(station)
            return ClinicalQueueService._format_called_entry(emergency)

        # Bước 2: Kiểm tra giới hạn (only for non-emergency)
        if active_count >= ClinicalQueueService.MAX_CONCURRENT_CALLS:
            return {
                'error': f'Đã đạt tối đa {ClinicalQueueService.MAX_CONCURRENT_CALLS} số đang gọi. '
                         'Hãy hoàn thành hoặc bỏ qua trước khi gọi tiếp.',
                'active_count': active_count,
            }
        
        # Bước 3: Gọi theo priority + FCFS
        next_entry = QueueEntry.objects.filter(
            station=station,
            status=QueueStatus.WAITING,
        ).order_by('-priority', 'entered_queue_time').first()
        
        if next_entry:
            next_entry.status = QueueStatus.CALLED
            next_entry.called_time = timezone.now()
            next_entry.save(update_fields=['status', 'called_time'])
            # Verify save succeeded
            next_entry.refresh_from_db()
            logger.info(
                '[CALL_NEXT] Called entry=%s station_id=%s status_after_save=%s',
                next_entry.id, next_entry.station_id, next_entry.status
            )
            # TTS: pre-generate for upcoming patients
            ClinicalQueueService._trigger_tts_pre_generate(station)
            return ClinicalQueueService._format_called_entry(next_entry)
        
        logger.info('[CALL_NEXT] Queue empty for station=%s', station.id)
        return None  # Hàng đợi trống

    @staticmethod
    def _format_called_entry(entry):
        """Format thông tin entry được gọi cho bảng LED / response"""
        visit = entry.queue_number.visit
        patient = visit.patient
        
        display_label = entry.queue_number.number_code
        if entry.source_type == QueueSourceType.ONLINE_BOOKING:
            display_label += " (Đặt lịch)"
        elif entry.source_type == QueueSourceType.EMERGENCY:
            display_label += " 🚨 CẤP CỨU"
        
        # Patient model dùng @property full_name (có underscore)
        patient_name = getattr(patient, 'full_name', None) or str(patient)

        # TTS: get pre-generated audio URL
        audio_url = None
        try:
            from .tts_service import get_audio_url
            audio_url = get_audio_url(str(entry.id))
        except Exception:
            pass  # TTS is best-effort, don't break the call flow
        
        return {
            'entry_id': str(entry.id),
            'visit_id': str(entry.queue_number.visit.id),
            'queue_number': entry.queue_number.number_code,
            'daily_sequence': entry.queue_number.daily_sequence,
            'patient_name': patient_name,
            'source_type': entry.source_type,
            'priority': entry.priority,
            'display_label': display_label,
            'station_code': entry.station.code,
            'station_name': entry.station.name,
            'wait_time_minutes': entry.wait_time_minutes,
            'status': entry.status,
            'audio_url': audio_url,
        }

    @staticmethod
    def _trigger_tts_pre_generate(station):
        """Trigger TTS pre-generation for upcoming patients (best-effort)."""
        try:
            from .tts_service import pre_generate_for_upcoming
            pre_generate_for_upcoming.delay(str(station.id))
        except Exception:
            import logging
            logging.getLogger('qms').exception('Failed to trigger TTS pre-generation')

    @staticmethod
    def get_queue_board(station):
        """
        Lấy danh sách hàng đợi cho bảng LED trước phòng khám.
        
        Returns:
            dict: {
                currently_serving: [{...}, ...],   # Array, max 3
                waiting_list: [{...}, ...],
                completed_list: [{...}, ...],      # Last 10 today
                total_waiting: int,
                estimated_wait_minutes: int,
            }
        """
        from datetime import date as date_cls
        import logging
        logger = logging.getLogger('qms')

        # Bệnh nhân đang khám / đã gọi (tối đa 3)
        active_entries = QueueEntry.objects.filter(
            station=station,
            status__in=[QueueStatus.IN_PROGRESS, QueueStatus.CALLED],
        ).order_by('-priority', 'called_time').select_related(
            'queue_number',
            'queue_number__visit',
            'queue_number__visit__patient',
        )

        # DEBUG: Log raw query results
        active_count = active_entries.count()
        logger.info(
            '[BOARD] station=%s (id=%s) active_entries_count=%d',
            station.code, station.id, active_count
        )
        if active_count == 0:
            # Check ALL entries at this station regardless of status
            all_entries = QueueEntry.objects.filter(station=station)
            for e in all_entries[:10]:
                logger.info(
                    '[BOARD] entry=%s status=%s station_id=%s source=%s',
                    e.id, e.status, e.station_id, e.source_type
                )
        
        currently_serving = []
        for entry in active_entries:
            try:
                currently_serving.append(
                    ClinicalQueueService._format_called_entry(entry)
                )
            except Exception as exc:
                logger.error('_format_called_entry failed for entry %s: %s', entry.id, exc)
        
        # Danh sách chờ
        waiting = QueueEntry.objects.filter(
            station=station,
            status=QueueStatus.WAITING,
        ).order_by('-priority', 'entered_queue_time').select_related(
            'queue_number',
            'queue_number__visit',
            'queue_number__visit__patient',
        )
        
        waiting_list = []
        for idx, entry in enumerate(waiting):
            try:
                patient = entry.queue_number.visit.patient
                patient_name = getattr(patient, 'full_name', None) or str(patient)
                waiting_list.append({
                    'position': idx + 1,
                    'entry_id': str(entry.id),
                    'queue_number': entry.queue_number.number_code,
                    'daily_sequence': entry.queue_number.daily_sequence,
                    'patient_name': patient_name,
                    'source_type': entry.source_type,
                    'priority': entry.priority,
                    'wait_time_minutes': entry.wait_time_minutes,
                })
            except Exception as exc:
                logger.error('waiting_list entry failed for entry %s: %s', entry.id, exc)

        # Danh sách đã hoàn thành hôm nay (COMPLETED/SKIPPED, last 10)
        done_entries = QueueEntry.objects.filter(
            station=station,
            status__in=[QueueStatus.COMPLETED, QueueStatus.SKIPPED],
            end_time__date=date_cls.today(),
        ).order_by('-end_time').select_related(
            'queue_number',
            'queue_number__visit',
            'queue_number__visit__patient',
        )[:10]

        completed_list = []
        for entry in done_entries:
            try:
                patient = entry.queue_number.visit.patient
                patient_name = getattr(patient, 'full_name', None) or str(patient)
                completed_list.append({
                    'entry_id': str(entry.id),
                    'queue_number': entry.queue_number.number_code,
                    'daily_sequence': entry.queue_number.daily_sequence,
                    'patient_name': patient_name,
                    'source_type': entry.source_type,
                    'status': entry.status,
                    'end_time': entry.end_time.strftime('%H:%M') if entry.end_time else None,
                })
            except Exception as exc:
                logger.error('completed_list entry failed for entry %s: %s', entry.id, exc)

        # Danh sách vắng hôm nay (NO_SHOW — có thể gọi lại)
        noshow_entries = QueueEntry.objects.filter(
            station=station,
            status=QueueStatus.NO_SHOW,
            end_time__date=date_cls.today(),
        ).order_by('-end_time').select_related(
            'queue_number',
            'queue_number__visit',
            'queue_number__visit__patient',
        )[:20]

        no_show_list = []
        for entry in noshow_entries:
            try:
                patient = entry.queue_number.visit.patient
                patient_name = getattr(patient, 'full_name', None) or str(patient)
                no_show_list.append({
                    'entry_id': str(entry.id),
                    'visit_id': str(entry.queue_number.visit.id),
                    'queue_number': entry.queue_number.number_code,
                    'daily_sequence': entry.queue_number.daily_sequence,
                    'patient_name': patient_name,
                    'source_type': entry.source_type,
                    'status': entry.status,
                    'end_time': entry.end_time.strftime('%H:%M') if entry.end_time else None,
                })
            except Exception as exc:
                logger.error('no_show_list entry failed for entry %s: %s', entry.id, exc)
        
        return {
            'station': {
                'code': station.code,
                'name': station.name,
            },
            'currently_serving': currently_serving,
            'waiting_list': waiting_list,
            'completed_list': completed_list,
            'no_show_list': no_show_list,
            'total_waiting': len(waiting_list),
            'estimated_wait_minutes': len(waiting_list) * 10,
        }

