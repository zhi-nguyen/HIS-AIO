from django.db import models
from apps.core_services.core.models import UUIDModel

class ServiceList(UUIDModel):
    name = models.CharField(max_length=255, verbose_name="Tên dịch vụ", help_text="Công thức máu, X-Quang Ngực...")
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã dịch vụ")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    category = models.CharField(max_length=50, verbose_name="Loại", help_text="Lab, Imaging, Functional Probing")

    def __str__(self):
        return f"{self.code} - {self.name}"

class ServiceOrder(UUIDModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Nháp'
        ORDERED = 'ORDERED', 'Đã chỉ định'
        PROCESSING = 'PROCESSING', 'Đang thực hiện'
        COMPLETED = 'COMPLETED', 'Hoàn thành'
        CANCELLED = 'CANCELLED', 'Hủy'

    visit = models.ForeignKey(
        'reception.Visit',
        on_delete=models.CASCADE,
        related_name='service_orders'
    )
    requester = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='service_requests'
    )
    service = models.ForeignKey(
        ServiceList,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    priority = models.CharField(max_length=20, default="ROUTINE", help_text="STAT, URGENT, ROUTINE")
    clinical_note = models.TextField(verbose_name="Chẩn đoán sơ bộ/Lý do chỉ định", null=True, blank=True)

    def __str__(self):
        return f"{self.service.name} for {self.visit.visit_code}"

class ServiceResult(UUIDModel):
    order = models.OneToOneField(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name='result'
    )
    performer = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='performed_services',
        null=True, blank=True
    )
    
    # Kết quả
    text_result = models.TextField(verbose_name="Kết quả chữ", null=True, blank=True)
    image_url = models.URLField(verbose_name="Link ảnh (DICOM/JPG)", null=True, blank=True)
    dicom_series_uid = models.CharField(max_length=255, null=True, blank=True)
    
    # AI Analysis for Results
    ai_analysis_json = models.JSONField(verbose_name="AI phân tích", null=True, blank=True)

    finalized_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Result for {self.order.pk}"
