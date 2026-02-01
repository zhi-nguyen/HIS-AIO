from django.db import models
from apps.core_services.core.models import UUIDModel


class RoomType(models.TextChoices):
    """Loại phòng bệnh"""
    STANDARD = 'STANDARD', 'Thường'
    VIP = 'VIP', 'VIP'
    ICU = 'ICU', 'Hồi sức tích cực'
    NICU = 'NICU', 'Hồi sức sơ sinh'
    ISOLATION = 'ISOLATION', 'Cách ly'


class AdmissionStatus(models.TextChoices):
    """Trạng thái nhập viện"""
    ACTIVE = 'ACTIVE', 'Đang điều trị'
    DISCHARGED = 'DISCHARGED', 'Đã xuất viện'
    TRANSFERRED = 'TRANSFERRED', 'Đã chuyển viện'
    DECEASED = 'DECEASED', 'Tử vong'


class Ward(UUIDModel):
    """
    Khoa nội trú
    Một khoa có nhiều phòng, mỗi phòng có nhiều giường
    """
    department = models.OneToOneField(
        'departments.Department',
        on_delete=models.CASCADE,
        related_name='ward',
        verbose_name="Khoa"
    )
    name = models.CharField(max_length=100, verbose_name="Tên khoa nội trú")
    code = models.CharField(max_length=20, unique=True, verbose_name="Mã khoa")
    
    # Statistics
    total_beds = models.IntegerField(default=0, verbose_name="Tổng số giường")
    
    # Contact
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Số điện thoại")
    floor = models.CharField(max_length=20, null=True, blank=True, verbose_name="Tầng")

    class Meta:
        verbose_name = "Khoa nội trú"
        verbose_name_plural = "Các khoa nội trú"

    def __str__(self):
        return f"[{self.code}] {self.name}"
    
    @property
    def available_beds(self):
        """Số giường còn trống"""
        return Bed.objects.filter(
            room__ward=self,
            status=Bed.Status.AVAILABLE
        ).count()


class Room(UUIDModel):
    """Phòng bệnh"""
    ward = models.ForeignKey(
        Ward, 
        on_delete=models.CASCADE, 
        related_name='rooms',
        verbose_name="Khoa"
    )
    room_number = models.CharField(max_length=20, verbose_name="Số phòng")
    room_type = models.CharField(
        max_length=20, 
        choices=RoomType.choices,
        default=RoomType.STANDARD,
        verbose_name="Loại phòng"
    )
    
    # Capacity
    total_beds = models.IntegerField(default=4, verbose_name="Số giường tối đa")
    
    # Pricing (for VIP rooms)
    daily_rate = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Giá phòng/ngày"
    )
    
    # Features
    has_bathroom = models.BooleanField(default=True, verbose_name="Có toilet riêng")
    has_ac = models.BooleanField(default=True, verbose_name="Có điều hòa")

    class Meta:
        verbose_name = "Phòng bệnh"
        verbose_name_plural = "Các phòng bệnh"
        unique_together = ['ward', 'room_number']

    def __str__(self):
        return f"Phòng {self.room_number} - {self.ward.code}"


class Bed(UUIDModel):
    """Giường bệnh"""
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Trống'
        OCCUPIED = 'OCCUPIED', 'Đang nằm'
        RESERVED = 'RESERVED', 'Đã đặt trước'
        CLEANING = 'CLEANING', 'Đang dọn'
        MAINTENANCE = 'MAINTENANCE', 'Bảo trì'
        OUT_OF_SERVICE = 'OUT_OF_SERVICE', 'Ngừng sử dụng'

    room = models.ForeignKey(
        Room, 
        on_delete=models.CASCADE, 
        related_name='beds',
        verbose_name="Phòng"
    )
    bed_number = models.CharField(max_length=10, verbose_name="Số giường")
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.AVAILABLE,
        verbose_name="Trạng thái"
    )
    
    # Current patient (if occupied)
    note = models.TextField(null=True, blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Giường bệnh"
        verbose_name_plural = "Các giường bệnh"
        unique_together = ['room', 'bed_number']

    def __str__(self):
        return f"Giường {self.bed_number} - {self.room}"


class Admission(UUIDModel):
    """
    Hồ sơ nhập viện
    Liên kết bệnh nhân với giường và theo dõi quá trình điều trị
    """
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='admissions',
        verbose_name="Bệnh nhân"
    )
    visit = models.ForeignKey(
        'reception.Visit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admission',
        verbose_name="Lượt khám gốc",
        help_text="Lượt khám ngoại trú dẫn đến nhập viện (nếu có)"
    )
    bed = models.ForeignKey(
        Bed,
        on_delete=models.PROTECT,
        related_name='admissions',
        verbose_name="Giường"
    )
    
    # Admission info
    admission_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Số hồ sơ nhập viện"
    )
    admission_time = models.DateTimeField(verbose_name="Thời gian nhập viện")
    admission_diagnosis = models.TextField(verbose_name="Chẩn đoán lúc nhập viện")
    
    # Admitting doctor
    admitting_doctor = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='admissions_admitted',
        verbose_name="Bác sĩ nhập viện"
    )
    
    # Discharge info
    discharge_time = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Thời gian xuất viện"
    )
    discharge_diagnosis = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Chẩn đoán lúc xuất viện"
    )
    discharge_summary = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Tóm tắt bệnh án"
    )
    discharging_doctor = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admissions_discharged',
        verbose_name="Bác sĩ xuất viện"
    )
    
    status = models.CharField(
        max_length=20,
        choices=AdmissionStatus.choices,
        default=AdmissionStatus.ACTIVE,
        verbose_name="Trạng thái"
    )
    
    # Transfer history tracking
    transfer_note = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Ghi chú chuyển khoa/giường"
    )

    class Meta:
        verbose_name = "Hồ sơ nhập viện"
        verbose_name_plural = "Các hồ sơ nhập viện"
        ordering = ['-admission_time']

    def __str__(self):
        return f"[{self.admission_number}] {self.patient.fullname}"
    
    @property
    def length_of_stay(self):
        """Số ngày nằm viện"""
        from django.utils import timezone
        end_time = self.discharge_time or timezone.now()
        delta = end_time - self.admission_time
        return delta.days


class DailyCare(UUIDModel):
    """
    Tờ điều trị hàng ngày
    Ghi nhận diễn biến, y lệnh thuốc, y lệnh chăm sóc mỗi ngày
    """
    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name='daily_cares',
        verbose_name="Hồ sơ nhập viện"
    )
    care_date = models.DateField(verbose_name="Ngày")
    
    # Clinical progress
    progress_note = models.TextField(
        verbose_name="Diễn biến",
        help_text="Tình trạng bệnh nhân trong ngày"
    )
    vital_signs = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Dấu hiệu sinh tồn",
        help_text="VD: {'blood_pressure': '120/80', 'heart_rate': 75, 'temperature': 37.0}"
    )
    
    # Orders
    medication_orders = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Y lệnh thuốc"
    )
    nursing_orders = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Y lệnh chăm sóc"
    )
    lab_orders_note = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Chỉ định xét nghiệm"
    )
    imaging_orders_note = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Chỉ định CĐHA"
    )
    
    # Doctor
    attending_doctor = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='daily_cares_attended',
        verbose_name="Bác sĩ điều trị"
    )
    
    created_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tờ điều trị"
        verbose_name_plural = "Các tờ điều trị"
        unique_together = ['admission', 'care_date']
        ordering = ['-care_date']

    def __str__(self):
        return f"Điều trị {self.care_date} - {self.admission.patient.fullname}"


class BedTransfer(UUIDModel):
    """
    Lịch sử chuyển giường/khoa
    Ghi nhận mỗi lần bệnh nhân được chuyển
    """
    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name='bed_transfers',
        verbose_name="Hồ sơ nhập viện"
    )
    
    from_bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transfers_from',
        verbose_name="Giường cũ"
    )
    to_bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transfers_to',
        verbose_name="Giường mới"
    )
    
    transfer_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian chuyển")
    reason = models.TextField(verbose_name="Lý do chuyển")
    
    ordered_by = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True,
        related_name='bed_transfers_ordered',
        verbose_name="Bác sĩ chỉ định"
    )

    class Meta:
        verbose_name = "Chuyển giường"
        verbose_name_plural = "Lịch sử chuyển giường"
        ordering = ['-transfer_time']

    def __str__(self):
        return f"Transfer {self.admission.patient.fullname}: {self.from_bed} -> {self.to_bed}"