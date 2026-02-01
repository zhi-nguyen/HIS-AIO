from django.db import models
from django.utils import timezone
from apps.core_services.core.models import UUIDModel


class DrugCategory(UUIDModel):
    """Nhóm thuốc: Kháng sinh, Giảm đau, Tim mạch..."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Tên nhóm")
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Nhóm thuốc"
        verbose_name_plural = "Các nhóm thuốc"

    def __str__(self):
        return self.name


class Medication(UUIDModel):
    """Danh mục thuốc"""
    category = models.ForeignKey(
        DrugCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medications',
        verbose_name="Nhóm thuốc"
    )
    
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã thuốc")
    name = models.CharField(max_length=255, verbose_name="Tên thuốc")
    active_ingredient = models.CharField(
        max_length=255, 
        verbose_name="Hoạt chất", 
        null=True, 
        blank=True
    )
    strength = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Hàm lượng",
        help_text="VD: 500mg, 10mg/ml"
    )
    dosage_form = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Dạng bào chế",
        help_text="VD: Viên nén, Viên nang, Dung dịch"
    )
    usage_route = models.CharField(
        max_length=50, 
        verbose_name="Đường dùng", 
        help_text="Uống, Tiêm, Bôi...", 
        null=True, 
        blank=True
    )
    
    unit = models.CharField(max_length=50, verbose_name="Đơn vị tính", default="Viên")
    
    # Pricing
    purchase_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Giá nhập"
    )
    selling_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Giá bán"
    )
    
    # Inventory (total across all lots)
    inventory_count = models.IntegerField(default=0, verbose_name="Tồn kho")
    min_stock = models.IntegerField(default=10, verbose_name="Tồn kho tối thiểu")
    
    # Flags
    requires_prescription = models.BooleanField(
        default=True, 
        verbose_name="Cần đơn thuốc"
    )
    is_active = models.BooleanField(default=True, verbose_name="Đang sử dụng")

    class Meta:
        verbose_name = "Thuốc"
        verbose_name_plural = "Danh mục thuốc"

    def __str__(self):
        return f"{self.name} ({self.active_ingredient})"


class MedicationLot(UUIDModel):
    """
    Quản lý lô thuốc - Lô/Hạn dùng (NEW)
    Mỗi lô có số lô riêng, ngày hết hạn, số lượng
    """
    medication = models.ForeignKey(
        Medication, 
        on_delete=models.CASCADE, 
        related_name='lots',
        verbose_name="Thuốc"
    )
    
    lot_number = models.CharField(max_length=50, verbose_name="Số lô")
    expiry_date = models.DateField(verbose_name="Ngày hết hạn")
    manufacture_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Ngày sản xuất"
    )
    
    # Quantity
    initial_quantity = models.IntegerField(default=0, verbose_name="Số lượng nhập")
    remaining_quantity = models.IntegerField(default=0, verbose_name="Số lượng còn lại")
    
    # Import info
    import_date = models.DateField(verbose_name="Ngày nhập")
    import_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Giá nhập"
    )
    supplier = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Nhà cung cấp"
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Đang sử dụng")

    class Meta:
        verbose_name = "Lô thuốc"
        verbose_name_plural = "Các lô thuốc"
        unique_together = ['medication', 'lot_number']
        ordering = ['expiry_date']  # FIFO: sort by expiry date

    def __str__(self):
        return f"{self.medication.name} - Lô {self.lot_number} - HSD: {self.expiry_date}"
    
    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()
    
    @property
    def days_until_expiry(self):
        delta = self.expiry_date - timezone.now().date()
        return delta.days


class Prescription(UUIDModel):
    """Đơn thuốc"""
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ phát thuốc'
        PARTIAL = 'PARTIAL', 'Đã phát một phần'
        DISPENSED = 'DISPENSED', 'Đã phát thuốc'
        CANCELLED = 'CANCELLED', 'Đã hủy'

    visit = models.ForeignKey(
        'reception.Visit',
        on_delete=models.CASCADE,
        related_name='prescriptions',
        verbose_name="Lượt khám"
    )
    doctor = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='prescriptions_prescribed',
        verbose_name="Bác sĩ kê đơn"
    )
    
    prescription_code = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Mã đơn thuốc"
    )
    prescription_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày kê đơn"
    )
    
    diagnosis = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Chẩn đoán"
    )
    note = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="Lời dặn bác sĩ"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Trạng thái"
    )
    
    # AI Analysis Fields
    ai_interaction_warning = models.TextField(
        null=True, 
        blank=True, 
        help_text="Cảnh báo tương tác thuốc từ AI"
    )
    
    # Total price
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Tổng tiền"
    )

    class Meta:
        verbose_name = "Đơn thuốc"
        verbose_name_plural = "Các đơn thuốc"

    def __str__(self):
        return f"Prescription for {self.visit.visit_code}"


class PrescriptionDetail(UUIDModel):
    """Chi tiết đơn thuốc"""
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name="Đơn thuốc"
    )
    medication = models.ForeignKey(
        Medication,
        on_delete=models.PROTECT,
        related_name='prescription_details',
        verbose_name="Thuốc"
    )
    
    quantity = models.IntegerField(verbose_name="Số lượng")
    usage_instruction = models.CharField(
        max_length=255, 
        verbose_name="Cách dùng", 
        help_text="Sáng 1, Chiều 1..."
    )
    duration_days = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Số ngày dùng"
    )
    
    # Price at time of prescription
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Đơn giá"
    )
    
    # Dispensed tracking
    dispensed_quantity = models.IntegerField(
        default=0,
        verbose_name="Đã phát"
    )

    class Meta:
        verbose_name = "Chi tiết đơn thuốc"
        verbose_name_plural = "Chi tiết đơn thuốc"

    def __str__(self):
        return f"{self.medication.name} x {self.quantity}"
    
    @property
    def remaining_quantity(self):
        return self.quantity - self.dispensed_quantity


class DispenseRecord(UUIDModel):
    """
    Ghi nhận xuất thuốc (NEW)
    Theo dõi mỗi lần phát thuốc từ lô nào
    """
    prescription_detail = models.ForeignKey(
        PrescriptionDetail,
        on_delete=models.CASCADE,
        related_name='dispense_records',
        verbose_name="Chi tiết đơn"
    )
    lot = models.ForeignKey(
        MedicationLot,
        on_delete=models.PROTECT,
        related_name='dispense_records',
        verbose_name="Lô thuốc"
    )
    
    quantity = models.IntegerField(verbose_name="Số lượng xuất")
    dispense_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Thời gian xuất"
    )
    
    pharmacist = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='dispenses_performed',
        verbose_name="Dược sĩ phát thuốc"
    )
    
    note = models.TextField(null=True, blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Phiếu xuất thuốc"
        verbose_name_plural = "Các phiếu xuất thuốc"

    def __str__(self):
        return f"Dispense {self.quantity} {self.lot.medication.name}"
    
    def save(self, *args, **kwargs):
        """Trừ kho khi xuất thuốc"""
        if not self.pk:  # Only on create
            # Deduct from lot
            self.lot.remaining_quantity -= self.quantity
            self.lot.save()
            
            # Update medication total inventory
            self.lot.medication.inventory_count -= self.quantity
            self.lot.medication.save()
            
            # Update prescription detail dispensed count
            self.prescription_detail.dispensed_quantity += self.quantity
            self.prescription_detail.save()
            
            # Update prescription status if fully dispensed
            prescription = self.prescription_detail.prescription
            all_dispensed = all(
                d.dispensed_quantity >= d.quantity 
                for d in prescription.details.all()
            )
            if all_dispensed:
                prescription.status = Prescription.Status.DISPENSED
            else:
                prescription.status = Prescription.Status.PARTIAL
            prescription.save()
        
        super().save(*args, **kwargs)
