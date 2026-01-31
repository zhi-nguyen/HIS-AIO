from django.db import models
from apps.core_services.core.models import UUIDModel


class ServiceType(models.TextChoices):
    """Loại dịch vụ"""
    CONSULTATION = 'CONSULTATION', 'Khám bệnh'
    LAB = 'LAB', 'Xét nghiệm'
    IMAGING = 'IMAGING', 'Chẩn đoán hình ảnh'
    PROCEDURE = 'PROCEDURE', 'Thủ thuật'
    SURGERY = 'SURGERY', 'Phẫu thuật'
    MEDICATION = 'MEDICATION', 'Thuốc'
    SUPPLIES = 'SUPPLIES', 'Vật tư'
    BED = 'BED', 'Giường bệnh'
    OTHER = 'OTHER', 'Khác'


class InvoiceStatus(models.TextChoices):
    """Trạng thái hóa đơn"""
    PENDING = 'PENDING', 'Chờ thanh toán'
    PARTIAL = 'PARTIAL', 'Thanh toán một phần'
    PAID = 'PAID', 'Đã thanh toán'
    CANCELLED = 'CANCELLED', 'Đã hủy'
    REFUNDED = 'REFUNDED', 'Đã hoàn tiền'


class PaymentMethod(models.TextChoices):
    """Phương thức thanh toán"""
    CASH = 'CASH', 'Tiền mặt'
    CARD = 'CARD', 'Thẻ ngân hàng'
    TRANSFER = 'TRANSFER', 'Chuyển khoản'
    MOMO = 'MOMO', 'Ví MoMo'
    VNPAY = 'VNPAY', 'VNPay'
    INSURANCE = 'INSURANCE', 'BHYT chi trả'


class PriceList(UUIDModel):
    """
    Bảng giá
    Có thể có nhiều bảng giá: BHYT, Dịch vụ thường, VIP, Nước ngoài...
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="Mã bảng giá")
    name = models.CharField(max_length=100, verbose_name="Tên bảng giá")
    description = models.TextField(null=True, blank=True)
    
    is_default = models.BooleanField(default=False, verbose_name="Bảng giá mặc định")
    is_active = models.BooleanField(default=True, verbose_name="Đang áp dụng")
    
    effective_from = models.DateField(null=True, blank=True, verbose_name="Áp dụng từ ngày")
    effective_to = models.DateField(null=True, blank=True, verbose_name="Áp dụng đến ngày")

    class Meta:
        verbose_name = "Bảng giá"
        verbose_name_plural = "Các bảng giá"

    def __str__(self):
        return f"[{self.code}] {self.name}"


class ServiceCatalog(UUIDModel):
    """
    Danh mục dịch vụ y tế
    Định nghĩa các dịch vụ có thể tính tiền
    """
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã dịch vụ")
    name = models.CharField(max_length=255, verbose_name="Tên dịch vụ")
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.OTHER,
        verbose_name="Loại dịch vụ"
    )
    
    # Base price (can be overridden by ServicePrice)
    base_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Giá cơ bản"
    )
    
    # BHYT info
    bhyt_code = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        verbose_name="Mã BHYT"
    )
    bhyt_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True,
        blank=True,
        verbose_name="Giá BHYT thanh toán"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Đang sử dụng")
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Danh mục dịch vụ"
        verbose_name_plural = "Danh mục dịch vụ"

    def __str__(self):
        return f"[{self.code}] {self.name}"


class ServicePrice(UUIDModel):
    """
    Giá dịch vụ theo từng bảng giá
    Cho phép một dịch vụ có nhiều mức giá khác nhau
    """
    service = models.ForeignKey(
        ServiceCatalog, 
        on_delete=models.CASCADE, 
        related_name='prices',
        verbose_name="Dịch vụ"
    )
    price_list = models.ForeignKey(
        PriceList, 
        on_delete=models.CASCADE, 
        related_name='service_prices',
        verbose_name="Bảng giá"
    )
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Giá"
    )

    class Meta:
        verbose_name = "Giá dịch vụ"
        verbose_name_plural = "Giá dịch vụ"
        unique_together = ['service', 'price_list']

    def __str__(self):
        return f"{self.service.name} - {self.price_list.name}: {self.price}"


class Invoice(UUIDModel):
    """
    Hóa đơn
    Tổng hợp các chi phí phát sinh trong một lượt khám hoặc nhập viện
    """
    visit = models.ForeignKey(
        'reception.Visit',
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name="Lượt khám"
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name="Bệnh nhân"
    )
    
    invoice_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Số hóa đơn"
    )
    
    # Price list used
    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invoices',
        verbose_name="Bảng giá áp dụng"
    )
    
    # Totals
    total_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name="Tổng tiền"
    )
    discount_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name="Giảm giá"
    )
    insurance_coverage = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name="BHYT chi trả"
    )
    patient_payable = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name="Bệnh nhân phải trả"
    )
    paid_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name="Đã thanh toán"
    )
    
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.PENDING,
        verbose_name="Trạng thái"
    )
    
    # Timestamps
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")
    updated_time = models.DateTimeField(auto_now=True)
    
    # Created by
    created_by = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True,
        related_name='invoices_created',
        verbose_name="Người tạo"
    )
    
    note = models.TextField(null=True, blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Hóa đơn"
        verbose_name_plural = "Các hóa đơn"
        ordering = ['-created_time']

    def __str__(self):
        return f"[{self.invoice_number}] {self.patient.fullname}"
    
    def calculate_totals(self):
        """Tính toán lại tổng tiền từ các line items"""
        from django.db.models import Sum
        total = self.items.aggregate(total=Sum('total_price'))['total'] or 0
        self.total_amount = total
        self.patient_payable = total - self.discount_amount - self.insurance_coverage
        self.save()


class InvoiceLineItem(UUIDModel):
    """
    Chi tiết hóa đơn
    Mỗi dòng tương ứng với một dịch vụ/thuốc được sử dụng
    """
    invoice = models.ForeignKey(
        Invoice, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name="Hóa đơn"
    )
    service = models.ForeignKey(
        ServiceCatalog,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invoice_items',
        verbose_name="Dịch vụ"
    )
    
    # Item info
    item_name = models.CharField(max_length=255, verbose_name="Tên mục")
    quantity = models.IntegerField(default=1, verbose_name="Số lượng")
    unit_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Đơn giá"
    )
    total_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Thành tiền"
    )
    
    # Insurance
    insurance_covered = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="BHYT thanh toán"
    )
    
    # Payment status
    is_paid = models.BooleanField(default=False, verbose_name="Đã thanh toán")
    
    # Reference to original order
    related_order_type = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        verbose_name="Loại phiếu gốc",
        help_text="VD: LAB_ORDER, IMAGING_ORDER, PRESCRIPTION"
    )
    related_order_id = models.UUIDField(
        null=True, 
        blank=True,
        verbose_name="ID phiếu gốc"
    )
    
    created_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chi tiết hóa đơn"
        verbose_name_plural = "Chi tiết hóa đơn"

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class Payment(UUIDModel):
    """
    Thanh toán
    Ghi nhận mỗi lần bệnh nhân thanh toán
    """
    invoice = models.ForeignKey(
        Invoice, 
        on_delete=models.CASCADE, 
        related_name='payments',
        verbose_name="Hóa đơn"
    )
    
    receipt_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Số phiếu thu"
    )
    
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name="Số tiền"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="Phương thức"
    )
    
    payment_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian thanh toán")
    
    cashier = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='payments_received',
        verbose_name="Thu ngân"
    )
    
    # For refunds
    is_refund = models.BooleanField(default=False, verbose_name="Là hoàn tiền")
    refund_reason = models.TextField(null=True, blank=True, verbose_name="Lý do hoàn tiền")
    
    note = models.TextField(null=True, blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Thanh toán"
        verbose_name_plural = "Các khoản thanh toán"
        ordering = ['-payment_time']

    def __str__(self):
        return f"[{self.receipt_number}] {self.amount:,.0f} VND"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update invoice paid amount
        from django.db.models import Sum
        total_paid = self.invoice.payments.filter(is_refund=False).aggregate(
            total=Sum('amount')
        )['total'] or 0
        total_refund = self.invoice.payments.filter(is_refund=True).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        self.invoice.paid_amount = total_paid - total_refund
        
        if self.invoice.paid_amount >= self.invoice.patient_payable:
            self.invoice.status = InvoiceStatus.PAID
        elif self.invoice.paid_amount > 0:
            self.invoice.status = InvoiceStatus.PARTIAL
        
        self.invoice.save()


class DepositPayment(UUIDModel):
    """
    Tạm ứng
    Ghi nhận tiền tạm ứng trước khi sử dụng dịch vụ
    """
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='deposits',
        verbose_name="Bệnh nhân"
    )
    visit = models.ForeignKey(
        'reception.Visit',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='deposits',
        verbose_name="Lượt khám"
    )
    
    receipt_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Số phiếu tạm ứng"
    )
    
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name="Số tiền tạm ứng"
    )
    used_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        default=0,
        verbose_name="Đã sử dụng"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="Phương thức"
    )
    
    deposit_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạm ứng")
    
    cashier = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='deposits_received',
        verbose_name="Thu ngân"
    )
    
    note = models.TextField(null=True, blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Tạm ứng"
        verbose_name_plural = "Các khoản tạm ứng"

    def __str__(self):
        return f"[{self.receipt_number}] Tạm ứng {self.amount:,.0f} VND"
    
    @property
    def remaining_amount(self):
        return self.amount - self.used_amount
