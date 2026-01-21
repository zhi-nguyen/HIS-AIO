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
        PRIORITY = 'PRIORITY', 'Ưu tiên (Người già/Trẻ em)'
        EMERGENCY = 'EMERGENCY', 'Cấp cứu (Code Red)'

    visit_code = models.CharField(max_length=20, unique=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CHECK_IN)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)

    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='visits'
    )

    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_visits'
    )

    assigned_staff = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_visits'
    )
    reason = models.TextField(max_length=500, null=True, blank=True)

    ai_prediction = models.JSONField(null=True, blank=True)
    
    medical_summary = models.TextField(null=True, blank=True)

    queue_number = models.IntegerField()

    def __str__(self):
        return f"Visit {self.visit_code} - {self.patient.fullname}"