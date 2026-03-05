from django.db import models
from uuid6 import uuid7

class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    version = models.IntegerField(default=1)


    class Meta:
        abstract = True

class Province(models.Model):
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=150, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['code']
        verbose_name = "Tỉnh/Thành phố"
        verbose_name_plural = "Tỉnh/Thành phố"

class Ward(models.Model):
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name='wards'
    )
    
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=150, null=True, blank=True)

    def __str__(self):
        return f"{self.name}, {self.province.name}"

    class Meta:
        ordering = ['code']
        verbose_name = "Xã/Phường"
        verbose_name_plural = "Xã/Phường"
        indexes = [
            models.Index(fields=['province', 'code']),
        ]

class ICD10Category(models.Model):
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    include = models.TextField(null=True, blank=True)
    exclude = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        ordering = ['code']
        verbose_name = "Mã ICD-10"
        verbose_name_plural = "Mã ICD-10"

class ICD10Subcategory(models.Model):
    category = models.ForeignKey(
        ICD10Category,
        on_delete=models.CASCADE,
        related_name='subcategories'
    )
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    include = models.TextField(null=True, blank=True)
    exclude = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        ordering = ['code']
        verbose_name = "Mã phụ ICD-10"
        verbose_name_plural = "Mã phụ ICD-10"

class ICD10Code(models.Model):
    subcategory = models.ForeignKey(
        ICD10Subcategory,
        on_delete=models.CASCADE,
        related_name='icd10_codes'
    )
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.TextField()
    description = models.TextField(null=True, blank=True)
    extra_info = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        ordering = ['code']
        verbose_name = "Mã chi tiết ICD-10"
        verbose_name_plural = "Mã chi tiết ICD-10"


class ICD11Code(models.Model):
    """Mã bệnh ICD-11 (WHO 2022) — bổ sung bên cạnh ICD-10 hiện có."""

    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Mã ICD-11 (ví dụ: CA40.0)"
    )
    title = models.CharField(max_length=500, help_text="Tên bệnh ICD-11 (tiếng Anh)")
    title_vi = models.CharField(
        max_length=500,
        null=True, blank=True,
        help_text="Tên bệnh ICD-11 (tiếng Việt)"
    )
    inclusions = models.TextField(null=True, blank=True)
    exclusions = models.TextField(null=True, blank=True)
    is_billable = models.BooleanField(
        default=True,
        help_text="Mã có thể dùng cho kê khai (leaf node)"
    )

    # Ánh xạ sang ICD-10 tương đương
    icd10_map = models.ManyToManyField(
        ICD10Code,
        blank=True,
        related_name='icd11_codes',
        verbose_name="Mã ICD-10 tương đương"
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.title}"

    class Meta:
        ordering = ['code']
        verbose_name = "Mã ICD-11"
        verbose_name_plural = "Mã ICD-11"


class TechnicalService(models.Model):
    """Danh mục dịch vụ kỹ thuật (DMKT) theo quy định BHYT."""

    class ServiceGroup(models.TextChoices):
        LABORATORY = 'XN', 'Xét nghiệm'
        IMAGING = 'CDHA', 'Chẩn đoán hình ảnh'
        SURGERY = 'PT', 'Phẫu thuật thủ thuật'
        REHABILITATION = 'PHCN', 'Phục hồi chức năng'
        CONSULTATION = 'KCB', 'Khám chữa bệnh'
        OTHER = 'KHAC', 'Khác'

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Mã dịch vụ kỹ thuật (mã BYT)"
    )
    name = models.CharField(max_length=500, verbose_name="Tên dịch vụ")
    group = models.CharField(
        max_length=10,
        choices=ServiceGroup.choices,
        default=ServiceGroup.OTHER,
        verbose_name="Nhóm dịch vụ"
    )
    unit = models.CharField(
        max_length=50,
        default="lần",
        verbose_name="Đơn vị tính"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Giá thu (VNĐ)"
    )
    bhyt_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Giá BHYT thanh toán"
    )
    is_covered_by_bhyt = models.BooleanField(
        default=False,
        verbose_name="BHYT chi trả"
    )
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        ordering = ['group', 'code']
        verbose_name = "Dịch vụ kỹ thuật"
        verbose_name_plural = "Danh mục dịch vụ kỹ thuật"
        indexes = [
            models.Index(fields=['group', 'code']),
        ]

