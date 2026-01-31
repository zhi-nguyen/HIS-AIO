from django.db import models
from apps.core_services.core.models import UUIDModel

class Medication(UUIDModel):
    name = models.CharField(max_length=255, verbose_name="Tên thuốc")
    active_ingredient = models.CharField(max_length=255, verbose_name="Hoạt chất", null=True, blank=True)
    usage_route = models.CharField(max_length=50, verbose_name="Đường dùng", help_text="Uống, Tiêm, Bôi...", null=True, blank=True)
    inventory_count = models.IntegerField(default=0, verbose_name="Tồn kho")
    unit = models.CharField(max_length=50, verbose_name="Đơn vị tính", default="Viên")

    def __str__(self):
        return f"{self.name} ({self.active_ingredient})"

class Prescription(UUIDModel):
    visit = models.ForeignKey(
        'reception.Visit',
        on_delete=models.CASCADE,
        related_name='prescriptions'
    )
    doctor = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='prescriptions_prescribed'
    )
    note = models.TextField(null=True, blank=True, verbose_name="Lời dặn bác sĩ")
    
    # AI Analysis Fields
    ai_interaction_warning = models.TextField(null=True, blank=True, help_text="Cảnh báo tương tác thuốc từ AI")

    def __str__(self):
        return f"Prescription for {self.visit.visit_code}"

class PrescriptionDetail(UUIDModel):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='details'
    )
    medication = models.ForeignKey(
        Medication,
        on_delete=models.PROTECT,
        related_name='prescription_details'
    )
    quantity = models.IntegerField(verbose_name="Số lượng")
    usage_instruction = models.CharField(max_length=255, verbose_name="Cách dùng", help_text="Sáng 1, Chiều 1...")

    def __str__(self):
        return f"{self.medication.name} x {self.quantity}"
