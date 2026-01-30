from django.db import models
from apps.core_services.core.models import UUIDModel
from django.core.exceptions import ValidationError
class Appointment(UUIDModel):
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Đã lên lịch'
        CHECKED_IN = 'CHECKED_IN', 'Đã tiếp đón'
        COMPLETED = 'COMPLETED', 'Đã hoàn thành'
        CANCELLED = 'CANCELLED', 'Đã hủy'
        NO_SHOW = 'NO_SHOW', 'Không đến'
        
    class Type(models.TextChoices):
        NEW_VISIT = 'NEW', 'Khám mới'
        RE_EXAM = 'RE_EXAM', 'Tái khám'
        TELEHEALTH = 'TELEHEALTH', 'Tư vấn từ xa'

    appointment_code = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    appointment_type = models.CharField(max_length=20, choices=Type.choices, default=Type.NEW_VISIT)

    scheduled_time = models.DateTimeField()

    visit = models.OneToOneField(
        'reception.Visit',
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='appointment_source'
    )

    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='appointments'
    )

    doctor = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='appointments'
    )

    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.PROTECT,
        related_name='appointments'
    )

    reason_for_visit = models.TextField()
    queue_number = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Appointment {self.appointment_code}"

    def clean(self):
        if self.doctor.department_link != self.department:
            raise ValidationError("Bác sĩ không thuộc khoa này.")
    
class AppointmentChat(UUIDModel):
    class Sender(models.TextChoices):
        STAFF = 'STAFF', 'Nhân viên y tế'
        PATIENT = 'PATIENT', 'Bệnh nhân'
        AGENT = 'AGENT', 'Agent hỗ trợ khách hàng'

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='chats'
    )
    need_staff_response = models.BooleanField(default=False)

    staff = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointment_chats'
    )

    sender = models.CharField(max_length=10, choices=Sender.choices)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(default=0)

    def __str__(self):
        return f"Chat from {self.sender} at {self.timestamp} for {self.appointment}"