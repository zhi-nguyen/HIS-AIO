"""
Model cơ sở dữ liệu tương tác thuốc.

CDSS Track 3: DrugInteraction thay thế logic hardcoded trong
pharmacist_agent/tools.py, cho phép quản trị viên thêm/sửa tương tác
qua Django Admin mà không cần sửa code.

Seed data: Xem fixtures/drug_interactions_seed.json
"""
from django.db import models
from django.db.models import Q


class DrugInteractionSeverity(models.TextChoices):
    MAJOR = 'MAJOR', 'Nghiêm trọng – KHÔNG dùng chung'
    MODERATE = 'MODERATE', 'Trung bình – Cần theo dõi chặt chẽ'
    MINOR = 'MINOR', 'Nhẹ – Có thể dùng, lưu ý theo dõi'


class DrugInteraction(models.Model):
    """
    Cơ sở dữ liệu tương tác giữa hai hoạt chất thuốc.

    Lưu ý: drug_a_name và drug_b_name lưu theo thứ tự A-Z để tránh duplicate.
    Mối quan hệ là đối xứng: lookup cần check cả (A,B) và (B,A).
    Manager DrugInteractionManager.find() xử lý điều này.
    """

    drug_a_name = models.CharField(
        max_length=255,
        verbose_name='Hoạt chất A (lowercase)',
        help_text='Tên hoạt chất viết thường, sắp xếp A-Z so với drug_b_name'
    )
    drug_b_name = models.CharField(
        max_length=255,
        verbose_name='Hoạt chất B (lowercase)',
    )
    severity = models.CharField(
        max_length=10,
        choices=DrugInteractionSeverity.choices,
        default=DrugInteractionSeverity.MODERATE,
        verbose_name='Mức độ nghiêm trọng'
    )
    description = models.TextField(
        verbose_name='Mô tả tương tác',
        help_text='Cơ chế và hậu quả lâm sàng'
    )
    recommendation = models.TextField(
        verbose_name='Khuyến nghị xử trí',
        help_text='Hướng dẫn xử trí: tránh dùng chung, theo dõi INR...'
    )
    references = models.TextField(
        null=True,
        blank=True,
        verbose_name='Tài liệu tham khảo',
        help_text='Nguồn: DrugBank, Micromedex, BNF...'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tương tác thuốc'
        verbose_name_plural = 'Cơ sở dữ liệu tương tác thuốc'
        # Đảm bảo không duplicate: lưu theo thứ tự A-Z
        unique_together = [['drug_a_name', 'drug_b_name']]
        indexes = [
            models.Index(fields=['drug_a_name'], name='ddi_drug_a_idx'),
            models.Index(fields=['drug_b_name'], name='ddi_drug_b_idx'),
            models.Index(fields=['severity'], name='ddi_severity_idx'),
        ]
        ordering = ['-severity', 'drug_a_name']

    def __str__(self):
        return f"{self.drug_a_name} + {self.drug_b_name} [{self.get_severity_display()}]"

    def save(self, *args, **kwargs):
        """Chuẩn hóa lowercase và sắp xếp A-Z trước khi lưu."""
        a = self.drug_a_name.lower().strip()
        b = self.drug_b_name.lower().strip()
        # Luôn lưu theo thứ tự A-Z để unique_together hoạt động đúng
        self.drug_a_name, self.drug_b_name = (a, b) if a <= b else (b, a)
        super().save(*args, **kwargs)

    @classmethod
    def find_interactions(cls, drug_names: list[str]) -> 'models.QuerySet':
        """
        Tìm tất cả tương tác giữa danh sách thuốc.

        Tạo N*(N-1)/2 cặp từ drug_names, query 1 lần với OR conditions.
        Đối xứng được xử lý bởi vì drug_a <= drug_b khi lưu.
        """
        if len(drug_names) < 2:
            return cls.objects.none()

        normalized = [n.lower().strip() for n in drug_names]
        q = Q()
        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                a, b = sorted([normalized[i], normalized[j]])
                q |= Q(drug_a_name=a, drug_b_name=b)

        return cls.objects.filter(q, is_active=True)
