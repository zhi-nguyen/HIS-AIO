"""
Model phác đồ điều trị chuẩn (Clinical Guidelines).

Track 2: ClinicalGuideline lưu các phác đồ điều trị được nạp vào
RAG vector database (collection 'guidelines') để AI tư vấn chính xác hơn.
"""
from django.db import models
from apps.core_services.core.models import UUIDModel, ICD10Code


class ClinicalGuideline(UUIDModel):
    """
    Phác đồ điều trị chuẩn (theo hướng dẫn Bộ Y tế / chuyên ngành).

    Các phác đồ này được embed vào RAG vector database qua management command
    `python manage.py load_guidelines`, cho phép clinical_agent tìm kiếm
    guideline phù hợp theo diagnostic keyword.
    """

    title = models.CharField(
        max_length=500,
        verbose_name='Tên phác đồ',
        help_text='VD: Phác đồ điều trị tăng huyết áp - BYT 2024'
    )
    content = models.TextField(
        verbose_name='Nội dung phác đồ',
        help_text='Nội dung đầy đủ (Markdown/plain text). Dùng để embed vào RAG.'
    )
    version = models.CharField(
        max_length=50,
        verbose_name='Phiên bản',
        help_text='VD: 2024-BYT-Rev3'
    )
    source = models.CharField(
        max_length=255,
        verbose_name='Nguồn',
        help_text='VD: Bộ Y tế 2024, Hội tim mạch học Việt Nam'
    )
    effective_date = models.DateField(
        null=True, blank=True,
        verbose_name='Ngày hiệu lực'
    )

    # Liên kết với ICD-10 để AI tìm đúng phác đồ theo chẩn đoán
    icd10_codes = models.ManyToManyField(
        ICD10Code,
        blank=True,
        related_name='guidelines',
        verbose_name='Mã ICD-10 liên quan',
        help_text='Các mã bệnh mà phác đồ này áp dụng'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Đang sử dụng',
        help_text='Chỉ những phác đồ is_active=True mới được nạp vào RAG'
    )

    def __str__(self):
        return f"{self.title} (v{self.version})"

    class Meta:
        verbose_name = 'Phác đồ điều trị'
        verbose_name_plural = 'Danh mục phác đồ điều trị'
        ordering = ['-effective_date', 'title']
        indexes = [
            models.Index(fields=['is_active', 'effective_date'], name='guideline_active_date_idx'),
        ]
