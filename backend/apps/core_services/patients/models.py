from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core_services.core.models import UUIDModel, Province, Ward

class Patient(UUIDModel):
    class Gender(models.TextChoices):
        MALE = 'M', _('Nam')
        FEMALE = 'F', _('Nữ')
        OTHER = 'O', _('Khác')

    patient_code = models.CharField(max_length=20, unique=True, db_index=True)

    id_card = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    insurance_number = models.CharField(max_length=30, null=True, blank=True)

    is_anonymous = models.BooleanField(default=False)

    is_merged = models.BooleanField(default=False)

    merged_into = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merged_records'
    )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.OTHER)
    
    contact_number = models.CharField(max_length=15, null=True, blank=True)

    province = models.ForeignKey(
        Province,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patients'
    )
    ward = models.ForeignKey(
        Ward,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patients'
    )
    address_detail = models.CharField(max_length=255, null=True, blank=True)


    def __str__(self):
        return f"{self.patient_code} - {self.last_name} {self.first_name}"

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"
    @property
    def full_address(self):
        parts = []
        if self.address_detail:
            parts.append(self.address_detail)
        if self.ward:
            parts.append(self.ward.name)
        if self.province:
            parts.append(self.province.name)
        
        return ", ".join(parts) if parts else "Không có địa chỉ"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.province and self.ward:
            if self.ward.province != self.province:
                raise ValidationError({'ward': _('Xã/Phường này không thuộc Tỉnh/Thành phố đã chọn.')})

