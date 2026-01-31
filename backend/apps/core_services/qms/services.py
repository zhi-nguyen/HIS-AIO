"""
QMS Services - Business logic for Queue Management System
"""
from datetime import date
from django.utils import timezone
from django.db import transaction
from django.db.models import Max

from .models import ServiceStation, QueueNumber, QueueEntry, QueueStatus, StationType


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
