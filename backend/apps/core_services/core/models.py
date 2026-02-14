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

