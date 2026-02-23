from django.db import models
from apps.core_services.core.models import UUIDModel


class FHIRServerConfig(UUIDModel):
    """
    Cấu hình kết nối tới FHIR Server bên ngoài.
    Có thể cấu hình nhiều server cho các mục đích khác nhau
    (ví dụ: 1 server cho BHXH, 1 server cho liên viện).
    """
    name = models.CharField(
        max_length=100,
        verbose_name="Tên cấu hình",
        help_text="VD: BHXH Gateway, Liên viện Server"
    )
    base_url = models.URLField(
        verbose_name="FHIR Server URL",
        help_text="VD: https://fhir.example.com/r4"
    )
    fhir_version = models.CharField(
        max_length=10,
        default='R4',
        verbose_name="Phiên bản FHIR"
    )
    auth_type = models.CharField(
        max_length=20,
        choices=[
            ('NONE', 'Không xác thực'),
            ('BEARER', 'Bearer Token'),
            ('BASIC', 'Basic Auth'),
            ('OAUTH2', 'OAuth2 Client Credentials'),
        ],
        default='NONE',
        verbose_name="Loại xác thực"
    )
    auth_token = models.TextField(
        null=True, blank=True,
        verbose_name="Token / Credentials",
        help_text="Bearer token hoặc base64(user:pass)"
    )
    timeout_seconds = models.IntegerField(
        default=30,
        verbose_name="Timeout (giây)"
    )

    class Meta:
        verbose_name = "Cấu hình FHIR Server"
        verbose_name_plural = "Cấu hình FHIR Server"

    def __str__(self):
        return f"{self.name} ({self.base_url})"


class PACSConfig(UUIDModel):
    """
    Cấu hình kết nối tới PACS Server (DICOMweb).
    Hỗ trợ WADO-RS, STOW-RS, QIDO-RS.
    """
    name = models.CharField(
        max_length=100,
        verbose_name="Tên PACS",
        help_text="VD: Orthanc chính, dcm4chee backup"
    )
    base_url = models.URLField(
        verbose_name="DICOMweb Base URL",
        help_text="VD: https://pacs.example.com/dicom-web"
    )
    ae_title = models.CharField(
        max_length=16,
        default='HIS_AIO',
        verbose_name="AE Title",
        help_text="Application Entity Title (tối đa 16 ký tự)"
    )
    auth_type = models.CharField(
        max_length=20,
        choices=[
            ('NONE', 'Không xác thực'),
            ('BEARER', 'Bearer Token'),
            ('BASIC', 'Basic Auth'),
        ],
        default='NONE',
        verbose_name="Loại xác thực"
    )
    auth_token = models.TextField(
        null=True, blank=True,
        verbose_name="Token / Credentials"
    )
    timeout_seconds = models.IntegerField(
        default=60,
        verbose_name="Timeout (giây)"
    )

    # DICOMweb endpoint paths (relative to base_url)
    wado_rs_path = models.CharField(
        max_length=100,
        default='/wado-rs',
        verbose_name="WADO-RS Path"
    )
    stow_rs_path = models.CharField(
        max_length=100,
        default='/stow-rs',
        verbose_name="STOW-RS Path"
    )
    qido_rs_path = models.CharField(
        max_length=100,
        default='/qido-rs',
        verbose_name="QIDO-RS Path"
    )

    class Meta:
        verbose_name = "Cấu hình PACS Server"
        verbose_name_plural = "Cấu hình PACS Server"

    def __str__(self):
        return f"{self.name} ({self.base_url})"


class InteropAuditLog(models.Model):
    """
    Audit log ghi nhận mỗi lần trao đổi dữ liệu liên thông.
    """
    class Direction(models.TextChoices):
        OUTBOUND = 'OUT', 'Gửi đi (Export)'
        INBOUND = 'IN', 'Nhận về (Import)'

    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Thành công'
        FAILED = 'FAILED', 'Thất bại'
        PARTIAL = 'PARTIAL', 'Thành công một phần'

    class Protocol(models.TextChoices):
        FHIR = 'FHIR', 'HL7 FHIR'
        DICOM = 'DICOM', 'DICOM'

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    direction = models.CharField(
        max_length=3,
        choices=Direction.choices,
        verbose_name="Chiều trao đổi"
    )
    protocol = models.CharField(
        max_length=5,
        choices=Protocol.choices,
        verbose_name="Giao thức"
    )
    resource_type = models.CharField(
        max_length=50,
        verbose_name="Loại tài nguyên",
        help_text="VD: Patient, Encounter, ImagingStudy"
    )
    resource_id = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="ID tài nguyên"
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        verbose_name="Trạng thái"
    )
    remote_server = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="Server đích/nguồn"
    )
    request_payload_size = models.IntegerField(
        null=True, blank=True,
        verbose_name="Kích thước request (bytes)"
    )
    response_payload_size = models.IntegerField(
        null=True, blank=True,
        verbose_name="Kích thước response (bytes)"
    )
    duration_ms = models.IntegerField(
        null=True, blank=True,
        verbose_name="Thời gian xử lý (ms)"
    )
    error_message = models.TextField(
        null=True, blank=True,
        verbose_name="Thông báo lỗi"
    )
    initiated_by = models.CharField(
        max_length=100,
        null=True, blank=True,
        verbose_name="Người/Hệ thống khởi tạo"
    )

    class Meta:
        verbose_name = "Nhật ký liên thông"
        verbose_name_plural = "Nhật ký liên thông"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['protocol', 'resource_type']),
            models.Index(fields=['status', 'timestamp']),
        ]

    def __str__(self):
        return (
            f"[{self.timestamp:%Y-%m-%d %H:%M}] "
            f"{self.get_direction_display()} {self.protocol} "
            f"{self.resource_type} — {self.get_status_display()}"
        )
