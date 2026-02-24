from django.db import models
from apps.core_services.core.models import UUIDModel

class Visit(UUIDModel):
    class Status(models.TextChoices):
        CHECK_IN = 'CHECK_IN', 'Đang Check-in/Khai báo'
        TRIAGE = 'TRIAGE', 'Đang phân luồng'
        WAITING = 'WAITING', 'Đang chờ bác sĩ'
        IN_PROGRESS = 'IN_PROGRESS', 'Đang khám'
        PENDING_RESULTS = 'PENDING_RESULTS', 'Chờ kết quả CLS'
        COMPLETED = 'COMPLETED', 'Đã hoàn thành'
        CANCELLED = 'CANCELLED', 'Đã hủy'

    class Priority(models.TextChoices):
        NORMAL = 'NORMAL', 'Bình thường'
        ONLINE_BOOKING = 'ONLINE_BOOKING', 'Đặt lịch hẹn'
        PRIORITY = 'PRIORITY', 'Ưu tiên (Người già/Trẻ em)'
        EMERGENCY = 'EMERGENCY', 'Cấp cứu (Code Red)'

    class TriageMethod(models.TextChoices):
        AI = 'AI', 'AI phân luồng'
        MANUAL = 'MANUAL', 'Thủ công (Reception)'

    visit_code = models.CharField(max_length=20, unique=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CHECK_IN)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)

    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='visits'
    )

    assigned_staff = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_visits'
    )

    # --- Triage Result Fields ---
    chief_complaint = models.TextField(null=True, blank=True, verbose_name='Lý do khám')
    vital_signs = models.JSONField(null=True, blank=True, verbose_name='Chỉ số sinh hiệu')
    triage_code = models.CharField(max_length=20, null=True, blank=True, verbose_name='Mã phân luồng')
    triage_ai_response = models.TextField(null=True, blank=True, verbose_name='Phản hồi AI')
    triage_confidence = models.IntegerField(null=True, blank=True, verbose_name='Độ tin cậy (%)')
    triage_key_factors = models.JSONField(null=True, blank=True, verbose_name='Cơ sở phân luồng')
    triage_matched_departments = models.JSONField(null=True, blank=True, verbose_name='Khoa phù hợp (AI)')
    recommended_department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='triage_visits',
        verbose_name='Khoa AI đề xuất'
    )
    confirmed_department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmed_visits',
        verbose_name='Khoa xác nhận'
    )
    triage_confirmed_at = models.DateTimeField(null=True, blank=True)
    triage_method = models.CharField(
        max_length=10,
        choices=TriageMethod.choices,
        null=True, blank=True,
        verbose_name='Cách phân luồng'
    )

    pending_merge = models.BooleanField(
        default=False,
        verbose_name='Chờ gộp hồ sơ',
        help_text='BN cấp cứu chưa xác định danh tính, cần gộp sau'
    )

    queue_number = models.IntegerField()

    def __str__(self):
        return f"Visit {self.visit_code} - {self.patient}"