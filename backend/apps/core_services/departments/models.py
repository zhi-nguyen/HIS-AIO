from django.db import models
from uuid6 import uuid7

class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False, unique=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    def __str__(self):
        return f"{self.name} ({self.code})"
    
class DepartmentMember(models.Model):
    class Position(models.TextChoices):
        HEAD = 'HEAD', 'Trưởng khoa'
        DEPUTY_HEAD = 'DEPUTY_HEAD', 'Phó khoa'
        HEAD_NURSE = 'HEAD_NURSE', 'Trưởng phòng điều dưỡng'
        MEDICAL_STAFF = 'MEDICAL_STAFF', 'Nhân viên y tế'
        NURSING_STAFF = 'NURSING_STAFF', 'Nhân viên điều dưỡng'
        SUPPORT_STAFF = 'SUPPORT_STAFF', 'Nhân viên hỗ trợ'

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False, unique=True)
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