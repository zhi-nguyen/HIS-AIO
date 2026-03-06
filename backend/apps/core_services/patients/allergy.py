"""
Model quản lý thông tin dị ứng của bệnh nhân.

CDSS Track 3: PatientAllergy được dùng bởi CDSSService để cảnh báo
khi bác sĩ kê đơn thuốc có hoạt chất mà bệnh nhân đã dị ứng.
"""
from django.db import models
from apps.core_services.core.models import UUIDModel


class PatientAllergy(UUIDModel):
    """Ghi nhận dị ứng của bệnh nhân (thuốc, thực phẩm, môi trường)."""

    class AllergenType(models.TextChoices):
        DRUG = 'DRUG', 'Thuốc'
        FOOD = 'FOOD', 'Thực phẩm'
        ENVIRONMENTAL = 'ENV', 'Môi trường (phấn hoa, bụi...)'
        OTHER = 'OTHER', 'Khác'

    class Severity(models.TextChoices):
        MILD = 'MILD', 'Nhẹ (nổi mẩn, ngứa)'
        MODERATE = 'MODERATE', 'Trung bình (phù, khó thở nhẹ)'
        SEVERE = 'SEVERE', 'Nặng (phù Quincke, khó thở nặng)'
        LIFE_THREATENING = 'LIFE_THREATENING', 'Đe dọa tính mạng (sốc phản vệ)'

    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='allergies',
        verbose_name='Bệnh nhân'
    )

    allergen_name = models.CharField(
        max_length=255,
        verbose_name='Tên chất gây dị ứng',
        help_text='Tên thuốc / thực phẩm / chất gây dị ứng (viết thường để so sánh dễ dàng)'
    )
    allergen_name_normalized = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name='Tên chuẩn hóa (lowercase)',
        help_text='Tự động tạo từ allergen_name.lower().strip() khi lưu'
    )
    allergen_type = models.CharField(
        max_length=10,
        choices=AllergenType.choices,
        default=AllergenType.DRUG,
        verbose_name='Loại dị ứng'
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MILD,
        verbose_name='Mức độ'
    )
    reaction_description = models.TextField(
        null=True,
        blank=True,
        verbose_name='Mô tả phản ứng',
        help_text='Mô tả chi tiết triệu chứng khi tiếp xúc dị nguyên'
    )

    confirmed_by = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_allergies',
        verbose_name='Bác sĩ xác nhận'
    )
    confirmed_date = models.DateField(null=True, blank=True, verbose_name='Ngày xác nhận')

    note = models.TextField(null=True, blank=True, verbose_name='Ghi chú thêm')

    def save(self, *args, **kwargs):
        """Tự động normalize tên dị nguyên khi lưu."""
        self.allergen_name_normalized = self.allergen_name.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} - Dị ứng: {self.allergen_name} ({self.get_severity_display()})"

    class Meta:
        verbose_name = 'Dị ứng bệnh nhân'
        verbose_name_plural = 'Danh sách dị ứng bệnh nhân'
        indexes = [
            models.Index(fields=['patient', 'allergen_type'], name='allergy_patient_type_idx'),
            models.Index(fields=['allergen_name_normalized'], name='allergy_name_norm_idx'),
        ]
        # Không cho phép ghi nhận trùng cùng dị nguyên cho 1 bệnh nhân
        unique_together = [['patient', 'allergen_name_normalized']]
