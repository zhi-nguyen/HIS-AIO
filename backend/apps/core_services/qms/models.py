from django.db import models
from django.utils import timezone
from apps.core_services.core.models import UUIDModel


class StationType(models.TextChoices):
    """Loại điểm dịch vụ"""
    RECEPTION = 'RECEPTION', 'Tiếp đón'
    TRIAGE = 'TRIAGE', 'Phân luồng'
    DOCTOR = 'DOCTOR', 'Phòng khám bác sĩ'
    LIS = 'LIS', 'Phòng xét nghiệm (Lấy mẫu)'
    RIS = 'RIS', 'Phòng chẩn đoán hình ảnh'
    PHARMACY = 'PHARMACY', 'Nhà thuốc'
    CASHIER = 'CASHIER', 'Thu ngân'


class QueueStatus(models.TextChoices):
    """Trạng thái trong hàng đợi"""
    WAITING = 'WAITING', 'Đang chờ'
    CALLED = 'CALLED', 'Đã gọi'
    IN_PROGRESS = 'IN_PROGRESS', 'Đang thực hiện'
    COMPLETED = 'COMPLETED', 'Hoàn thành'
    SKIPPED = 'SKIPPED', 'Bỏ qua'
    NO_SHOW = 'NO_SHOW', 'Không có mặt'


class QueueSourceType(models.TextChoices):
    """Nguồn gốc vào hàng chờ — phân biệt 3 luồng bệnh nhân"""
    WALK_IN = 'WALK_IN', 'Vãng lai'
    ONLINE_BOOKING = 'ONLINE_BOOKING', 'Đặt lịch từ xa'
    EMERGENCY = 'EMERGENCY', 'Cấp cứu'


class ServiceStation(UUIDModel):
    """
    Điểm dịch vụ - nơi bệnh nhân cần đến
    VD: Phòng khám số 1, Phòng xét nghiệm, Nhà thuốc...
    """
    code = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Mã điểm dịch vụ",
        help_text="VD: PK01, LIS01, PHARMACY01"
    )
    name = models.CharField(max_length=100, verbose_name="Tên điểm dịch vụ")
    station_type = models.CharField(
        max_length=20, 
        choices=StationType.choices,
        verbose_name="Loại điểm"
    )
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.CASCADE,
        related_name='service_stations',
        verbose_name="Khoa/Phòng",
        null=True,
        blank=True
    )
    room_location = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        verbose_name="Vị trí phòng",
        help_text="VD: Tầng 1 - Dãy A"
    )
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    
    # Assigned staff (optional)
    current_staff = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_stations',
        verbose_name="Nhân viên phụ trách"
    )

    class Meta:
        verbose_name = "Điểm dịch vụ"
        verbose_name_plural = "Các điểm dịch vụ"
        ordering = ['station_type', 'code']

    def __str__(self):
        return f"[{self.code}] {self.name}"


class QueueNumber(UUIDModel):
    """
    Số thứ tự - được sinh ra khi bệnh nhân check-in hoặc chuyển tới station mới
    """
    number_code = models.CharField(
        max_length=30, 
        unique=True,
        verbose_name="Mã số thứ tự",
        help_text="VD: PK01-2026013101-005"
    )
    daily_sequence = models.IntegerField(verbose_name="Số thứ tự trong ngày")
    
    visit = models.ForeignKey(
        'reception.Visit',
        on_delete=models.CASCADE,
        related_name='queue_numbers',
        verbose_name="Lượt khám"
    )
    station = models.ForeignKey(
        ServiceStation,
        on_delete=models.CASCADE,
        related_name='queue_numbers',
        verbose_name="Điểm dịch vụ"
    )
    
    created_date = models.DateField(
        default=timezone.now,
        verbose_name="Ngày tạo"
    )
    created_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Thời gian tạo"
    )

    class Meta:
        verbose_name = "Số thứ tự"
        verbose_name_plural = "Các số thứ tự"
        ordering = ['created_date', 'daily_sequence']
        # Unique per station per day per sequence
        unique_together = ['station', 'created_date', 'daily_sequence']

    def __str__(self):
        return self.number_code


class QueueEntry(UUIDModel):
    """
    Phiếu xếp hàng - theo dõi trạng thái của bệnh nhân tại mỗi điểm dịch vụ
    """
    queue_number = models.ForeignKey(
        QueueNumber,
        on_delete=models.CASCADE,
        related_name='entries',
        verbose_name="Số thứ tự"
    )
    station = models.ForeignKey(
        ServiceStation,
        on_delete=models.CASCADE,
        related_name='queue_entries',
        verbose_name="Điểm dịch vụ"
    )
    
    status = models.CharField(
        max_length=20,
        choices=QueueStatus.choices,
        default=QueueStatus.WAITING,
        verbose_name="Trạng thái"
    )
    
    # Timestamps for tracking
    entered_queue_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Thời gian vào hàng đợi"
    )
    called_time = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Thời gian gọi"
    )
    start_time = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Thời gian bắt đầu phục vụ"
    )
    end_time = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Thời gian kết thúc"
    )
    
    # Priority for queue ordering
    priority = models.IntegerField(
        default=0,
        verbose_name="Độ ưu tiên",
        help_text="Emergency=100, Booking đúng giờ=7, Booking trễ=3, Walk-in=0"
    )
    
    # --- 3-Stream Queue Fields ---
    source_type = models.CharField(
        max_length=20,
        choices=QueueSourceType.choices,
        default=QueueSourceType.WALK_IN,
        verbose_name="Nguồn vào hàng chờ"
    )
    booking_ref = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='queue_entries',
        verbose_name="Lịch hẹn gốc"
    )
    
    # Notes
    note = models.TextField(null=True, blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Phiếu xếp hàng"
        verbose_name_plural = "Các phiếu xếp hàng"
        ordering = ['-priority', 'entered_queue_time']

    def __str__(self):
        return f"{self.queue_number.number_code} @ {self.station.code} - {self.status}"
    
    @property
    def wait_time_minutes(self):
        """Tính thời gian chờ (phút)"""
        if self.start_time and self.entered_queue_time:
            delta = self.start_time - self.entered_queue_time
            return int(delta.total_seconds() / 60)
        elif self.status == QueueStatus.WAITING:
            delta = timezone.now() - self.entered_queue_time
            return int(delta.total_seconds() / 60)
        return None
