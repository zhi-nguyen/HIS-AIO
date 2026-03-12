from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from apps.core_services.core.models import UUIDModel

import logging
logger = logging.getLogger(__name__)


class Modality(UUIDModel):
    """
    Loại thiết bị chẩn đoán hình ảnh
    VD: X-Quang, CT, MRI, Siêu âm...
    """
    code = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Mã loại máy",
        help_text="VD: XR, CT, MRI, US"
    )
    name = models.CharField(max_length=100, verbose_name="Tên loại máy")
    
    room_location = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        verbose_name="Vị trí phòng",
        help_text="VD: Tầng 2 - Phòng 201"
    )
    
    # Pricing
    base_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Giá cơ bản"
    )
    
    # Availability
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    
    # Turnaround time
    turnaround_time = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Thời gian trả kết quả (phút)",
        help_text="Thời gian dự kiến để có kết quả đọc"
    )

    class Meta:
        verbose_name = "Loại thiết bị CĐHA"
        verbose_name_plural = "Các loại thiết bị CĐHA"

    def __str__(self):
        return f"[{self.code}] {self.name}"


class ImagingProcedure(UUIDModel):
    """
    Danh mục kỹ thuật chẩn đoán hình ảnh
    Mỗi kỹ thuật thuộc về một loại máy (Modality)
    """
    modality = models.ForeignKey(
        Modality, 
        on_delete=models.PROTECT, 
        related_name='procedures',
        verbose_name="Loại máy"
    )
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã kỹ thuật")
    name = models.CharField(max_length=255, verbose_name="Tên kỹ thuật")
    body_part = models.CharField(
        max_length=100, 
        verbose_name="Vùng chụp",
        help_text="VD: Ngực, Bụng, Đầu, Cột sống..."
    )
    
    # Pricing can override modality base price
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Giá tiền"
    )
    
    # Preparation instructions
    preparation = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Hướng dẫn chuẩn bị",
        help_text="VD: Nhịn ăn 6h, uống thuốc cản quang..."
    )
    
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Kỹ thuật CĐHA"
        verbose_name_plural = "Các kỹ thuật CĐHA"

    def __str__(self):
        return f"[{self.code}] {self.name}"


class ImagingOrder(UUIDModel):
    """
    Phiếu chỉ định chẩn đoán hình ảnh
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ thực hiện'
        SCHEDULED = 'SCHEDULED', 'Đã lên lịch'
        IN_PROGRESS = 'IN_PROGRESS', 'Đang chụp'
        COMPLETED = 'COMPLETED', 'Đã chụp, chờ đọc'
        REPORTED = 'REPORTED', 'Đã có kết quả'
        VERIFIED = 'VERIFIED', 'Đã duyệt kết quả'
        CANCELLED = 'CANCELLED', 'Đã hủy'

    class Priority(models.TextChoices):
        NORMAL = 'NORMAL', 'Bình thường'
        URGENT = 'URGENT', 'Khẩn'
        STAT = 'STAT', 'Cấp cứu'

    visit = models.ForeignKey(
        'reception.Visit',
        on_delete=models.CASCADE,
        related_name='imaging_orders',
        verbose_name="Lượt khám"
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='imaging_orders',
        verbose_name="Bệnh nhân"
    )
    doctor = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='imaging_orders_created',
        verbose_name="Bác sĩ chỉ định"
    )
    
    procedure = models.ForeignKey(
        ImagingProcedure,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="Kỹ thuật chụp"
    )
    
    clinical_indication = models.TextField(
        verbose_name="Lý do chỉ định/Chẩn đoán lâm sàng",
        help_text="Mô tả triệu chứng hoặc chẩn đoán để bác sĩ CĐHA tham khảo"
    )
    
    accession_number = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Mã chỉ định CLS",
        help_text="Accession Number dùng để match với DICOM study từ Orthanc"
    )
    
    order_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian chỉ định")
    scheduled_time = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Thời gian hẹn chụp"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING,
        verbose_name="Trạng thái"
    )
    priority = models.CharField(
        max_length=20, 
        choices=Priority.choices, 
        default=Priority.NORMAL,
        verbose_name="Độ ưu tiên"
    )
    
    # Price at time of order
    price_at_time = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Giá lúc chỉ định"
    )
    
    note = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="Ghi chú"
    )

    class Meta:
        verbose_name = "Phiếu chỉ định CĐHA"
        verbose_name_plural = "Các phiếu chỉ định CĐHA"
        ordering = ['-order_time']

    def __str__(self):
        return f"Imaging Order {self.procedure.code} for {self.visit.visit_code}"
    
    def save(self, *args, **kwargs):
        if not self.price_at_time and self.procedure:
            self.price_at_time = self.procedure.price
        super().save(*args, **kwargs)


class ImagingExecution(UUIDModel):
    """
    Thông tin thực hiện chụp
    Ghi nhận thời gian và nhân viên thực hiện
    """
    order = models.OneToOneField(
        ImagingOrder,
        on_delete=models.CASCADE,
        related_name='execution',
        verbose_name="Phiếu chỉ định"
    )
    
    technician = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True,
        related_name='imaging_executed',
        verbose_name="Kỹ thuật viên thực hiện"
    )
    
    execution_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Thời gian thực hiện"
    )
    
    machine_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Mã máy chụp"
    )
    
    # DICOM Study UID for PACS integration
    dicom_study_uid = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="DICOM Study UID",
        help_text="UID để link với PACS server"
    )
    
    # Orthanc Instance ID for preview
    orthanc_instance_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Orthanc Instance ID",
        help_text="ID của instance đầu tiên/chính để lấy preview"
    )
    
    # Thumbnail/Preview URL
    thumbnail_url = models.URLField(
        null=True,
        blank=True,
        verbose_name="URL ảnh preview"
    )
    
    execution_note = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Ghi chú khi chụp"
    )

    class Meta:
        verbose_name = "Thực hiện chụp"
        verbose_name_plural = "Các lần thực hiện chụp"

    def __str__(self):
        return f"Execution for {self.order}"


class ImagingResult(UUIDModel):
    """
    Kết quả đọc phim / Báo cáo CĐHA
    """
    order = models.OneToOneField(
        ImagingOrder,
        on_delete=models.CASCADE,
        related_name='result',
        verbose_name="Phiếu chỉ định"
    )
    
    # Report content
    findings = models.TextField(
        verbose_name="Mô tả hình ảnh",
        help_text="Chi tiết những gì quan sát được trên phim"
    )
    conclusion = models.TextField(
        verbose_name="Kết luận",
        help_text="Kết luận chẩn đoán của bác sĩ CĐHA"
    )
    recommendation = models.TextField(
        null=True,
        blank=True,
        verbose_name="Đề xuất/Khuyến nghị"
    )
    
    # Radiologist info
    radiologist = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='imaging_reports',
        verbose_name="Bác sĩ đọc kết quả"
    )
    report_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Thời gian đọc kết quả"
    )
    
    # Verification
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Đã duyệt"
    )
    verified_by = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imaging_results_verified',
        verbose_name="Bác sĩ duyệt"
    )
    verified_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Thời gian duyệt"
    )
    
    # Flags
    is_abnormal = models.BooleanField(
        default=False,
        verbose_name="Bất thường"
    )
    is_critical = models.BooleanField(
        default=False,
        verbose_name="Nguy hiểm (Critical)",
        help_text="Cần báo ngay cho bác sĩ lâm sàng"
    )

    class Meta:
        verbose_name = "Kết quả CĐHA"
        verbose_name_plural = "Các kết quả CĐHA"

    def __str__(self):
        return f"Result for {self.order}"


# ==========================================================================
# WebSocket Signal — Thông báo realtime khi ImagingOrder thay đổi
# ==========================================================================
@receiver(post_save, sender=ImagingOrder)
def imaging_order_post_save(sender, instance, created, **kwargs):
    """Bắn WebSocket event khi ImagingOrder được CẬP NHẬT status. 
    
    QUAN TRỌNG: Không bắn khi created=True (tạo mới) vì BillingService đã xử lý
    việc thông báo đến RIS sau khi thanh toán thành công.
    """
    logger.info(f"ImagingOrder post_save triggered for {instance.id}, created={created}")

    # Chỉ bắn WS khi ORDER được cập nhật (không phải khi vừa tạo mới).
    # Khi vừa tạo mới (created=True), BillingService sẽ tự gửi thông báo đến ris_updates
    # thông qua transaction.on_commit sau khi thanh toán hoàn tất.
    if created:
        logger.info(f"ImagingOrder {instance.id} newly created — WS notification handled by BillingService.")
        return

    def send_ws_update():
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                "ris_updates",
                {
                    "type": "ris.order_updated",
                    "action": "updated",
                    "order_id": str(instance.id),
                    "status": instance.status,
                }
            )

            # Gửi đến Clinical / EMR để tự động refresh kết quả khi có báo cáo
            if instance.status in [ImagingOrder.Status.REPORTED, ImagingOrder.Status.VERIFIED]:
                visit_id_str = str(instance.visit_id)

                # Đính kèm mô tả và kết luận hình ảnh để AI re-analyse
                findings = ''
                conclusion = ''
                procedure_name = ''
                is_abnormal = False
                try:
                    result = getattr(instance, 'result', None)
                    if result:
                        findings = result.findings or ''
                        conclusion = result.conclusion or ''
                        is_abnormal = result.is_abnormal or False
                    procedure_name = getattr(instance.procedure, 'name', '') if instance.procedure else ''
                except Exception:
                    pass

                async_to_sync(channel_layer.group_send)(
                    f"clinical_visit_{visit_id_str}",
                    {
                        "type": "clinical.cls_updated",
                        "service_type": "ris",
                        "order_id": str(instance.id),
                        "status": instance.status,
                        "procedure_name": procedure_name,
                        "findings": findings,
                        "conclusion": conclusion,
                        "is_abnormal": is_abnormal,
                    }
                )
                logger.info(f"Pushed clinical.cls_updated (ris) for visit {visit_id_str}, status={instance.status}")
        else:
            logger.error("CHANNEL_LAYER is NONE, no RIS ws message sent.")

    transaction.on_commit(send_ws_update)
