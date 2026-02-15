from django.db import models
from apps.core_services.core.models import UUIDModel

class Department(UUIDModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(
        blank=True, default='',
        help_text='Mô tả chi tiết chức năng khoa phòng'
    )
    specialties = models.TextField(
        blank=True, default='',
        help_text='Danh sách chuyên khoa, ngăn bởi dấu phẩy'
    )
    typical_symptoms = models.TextField(
        blank=True, default='',
        help_text='Triệu chứng thường gặp để AI phân loại khoa phòng'
    )

    def __str__(self):
        return f"{self.name} ({self.code})"
    
class DepartmentMember(UUIDModel):
    class Position(models.TextChoices):
        HEAD = 'HEAD', 'Trưởng khoa'
        DEPUTY_HEAD = 'DEPUTY_HEAD', 'Phó khoa'
        HEAD_NURSE = 'HEAD_NURSE', 'Trưởng phòng điều dưỡng'
        MEDICAL_STAFF = 'MEDICAL_STAFF', 'Nhân viên y tế'
        NURSING_STAFF = 'NURSING_STAFF', 'Nhân viên điều dưỡng'
        SUPPORT_STAFF = 'SUPPORT_STAFF', 'Nhân viên hỗ trợ'
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='members'
    )
    staff = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.CASCADE,
        related_name='department_assignments'
    )
    position = models.CharField(max_length=20, choices=Position.choices)
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_primary = models.BooleanField(default=True)

    class Meta:
        unique_together = ('department', 'staff')

    def __str__(self):
        return f"{self.staff} - {self.position} tại {self.department.code}"