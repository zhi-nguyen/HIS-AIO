from django.db import models
from apps.core_services.core.models import UUIDModel


class LabCategory(UUIDModel):
    """Nhóm xét nghiệm: Huyết học, Sinh hóa, Vi sinh, MDB"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nhóm xét nghiệm")
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Nhóm xét nghiệm"
        verbose_name_plural = "Các nhóm xét nghiệm"

    def __str__(self):
        return self.name


class LabTest(UUIDModel):
    """Định nghĩa chỉ số xét nghiệm"""
    category = models.ForeignKey(LabCategory, on_delete=models.PROTECT, related_name='tests', verbose_name="Nhóm")
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã xét nghiệm")
    name = models.CharField(max_length=255, verbose_name="Tên xét nghiệm")
    unit = models.CharField(max_length=50, null=True, blank=True, verbose_name="Đơn vị")
    
    min_limit = models.FloatField(null=True, blank=True, verbose_name="Chỉ số thấp nhất (Bình thường)")
    max_limit = models.FloatField(null=True, blank=True, verbose_name="Chỉ số cao nhất (Bình thường)")
    
    # Panic/Critical values
    panic_low = models.FloatField(null=True, blank=True, verbose_name="Ngưỡng nguy hiểm thấp")
    panic_high = models.FloatField(null=True, blank=True, verbose_name="Ngưỡng nguy hiểm cao")
    
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Giá tiền")
    
    # Turnaround time (NEW)
    turnaround_time = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="Thời gian trả kết quả (phút)",
        help_text="Thời gian dự kiến để có kết quả, tính bằng phút"
    )
    
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Chỉ số xét nghiệm"
        verbose_name_plural = "Các chỉ số xét nghiệm"

    def __str__(self):
        return f"[{self.code}] {self.name}"

class LabOrder(UUIDModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ lấy mẫu'
        SAMPLING = 'SAMPLING', 'Đã lấy mẫu'
        PROCESSING = 'PROCESSING', 'Đang thực hiện'
        COMPLETED = 'COMPLETED', 'Đã có kết quả'
        CANCELLED = 'CANCELLED', 'Đã hủy'

    visit = models.ForeignKey(
        'reception.Visit',
        on_delete=models.CASCADE,
        related_name='lab_orders'
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='lab_orders'
    )
    # Ordering doctor
    doctor = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='lab_orders_created'
    )
    
    order_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    note = models.TextField(null=True, blank=True, verbose_name="Ghi chú lâm sàng")

    def __str__(self):
        return f"Lab Order for {self.visit.visit_code} - {self.status}"

class LabOrderDetail(UUIDModel):
    """Chi tiết phiếu xét nghiệm - liên kết LabOrder với LabTest"""
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='details')
    test = models.ForeignKey(LabTest, on_delete=models.PROTECT, related_name='order_details')
    price_at_time = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ('order', 'test')
        verbose_name = "Chi tiết phiếu xét nghiệm"
        verbose_name_plural = "Các chi tiết phiếu xét nghiệm"

    def __str__(self):
        return f"{self.test.name} in {self.order}"


class LabSample(UUIDModel):
    """
    Quản lý mẫu bệnh phẩm (NEW)
    - Theo dõi trạng thái mẫu từ lúc chờ lấy đến khi lab nhận
    - Barcode để định danh
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ lấy mẫu'
        COLLECTED = 'COLLECTED', 'Đã lấy mẫu'
        IN_TRANSIT = 'IN_TRANSIT', 'Đang vận chuyển'
        RECEIVED = 'RECEIVED', 'Lab đã nhận'
        PROCESSING = 'PROCESSING', 'Đang xét nghiệm'
        REJECTED = 'REJECTED', 'Mẫu bị từ chối'

    class SampleType(models.TextChoices):
        BLOOD = 'BLOOD', 'Máu'
        URINE = 'URINE', 'Nước tiểu'
        STOOL = 'STOOL', 'Phân'
        SPUTUM = 'SPUTUM', 'Đờm'
        CSF = 'CSF', 'Dịch não tủy'
        TISSUE = 'TISSUE', 'Mô'
        SWAB = 'SWAB', 'Dịch ngoáy'
        OTHER = 'OTHER', 'Khác'

    order = models.ForeignKey(
        LabOrder, 
        on_delete=models.CASCADE, 
        related_name='samples',
        verbose_name="Phiếu xét nghiệm"
    )
    
    barcode = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Mã vạch",
        help_text="Barcode dán trên ống nghiệm"
    )
    sample_type = models.CharField(
        max_length=20, 
        choices=SampleType.choices,
        default=SampleType.BLOOD,
        verbose_name="Loại mẫu"
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING,
        verbose_name="Trạng thái"
    )
    
    # Collection info
    collection_time = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Thời gian lấy mẫu"
    )
    collector = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='samples_collected',
        verbose_name="Người lấy mẫu"
    )
    collection_note = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="Ghi chú khi lấy mẫu"
    )
    
    # Receiving info
    received_time = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Thời gian lab nhận mẫu"
    )
    receiver = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='samples_received',
        verbose_name="Nhân viên nhận mẫu"
    )
    
    # Rejection info
    rejection_reason = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="Lý do từ chối mẫu",
        help_text="VD: Mẫu bị vỡ, không đủ lượng, sai định danh..."
    )
    rejected_time = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Thời gian từ chối"
    )

    class Meta:
        verbose_name = "Mẫu bệnh phẩm"
        verbose_name_plural = "Các mẫu bệnh phẩm"
        ordering = ['-collection_time']

    def __str__(self):
        return f"[{self.barcode}] {self.get_sample_type_display()} - {self.get_status_display()}"


class LabResult(UUIDModel):
    """Kết quả xét nghiệm chi tiết"""
    detail = models.OneToOneField(LabOrderDetail, on_delete=models.CASCADE, related_name='result')
    
    value_string = models.CharField(max_length=255, verbose_name="Kết quả (Chuỗi)")
    value_numeric = models.FloatField(null=True, blank=True, verbose_name="Kết quả (Số)")
    
    is_abnormal = models.BooleanField(default=False, verbose_name="Bất thường")
    is_critical = models.BooleanField(default=False, verbose_name="Nguy hiểm (Critical)")
    abnormal_flag = models.CharField(
        max_length=10, 
        null=True, 
        blank=True,
        verbose_name="Cờ bất thường",
        help_text="H=High, L=Low, HH=Critical High, LL=Critical Low"
    )
    
    machine_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Tên máy xét nghiệm")
    result_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian có kết quả")
    
    technician = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lab_results_processed',
        verbose_name="Kỹ thuật viên thực hiện"
    )
    
    # Verification fields (NEW)
    is_verified = models.BooleanField(
        default=False, 
        verbose_name="Đã duyệt",
        help_text="Bác sĩ xét nghiệm đã xác nhận kết quả"
    )
    verified_by = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='lab_results_verified',
        verbose_name="Bác sĩ duyệt kết quả"
    )
    verified_time = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Thời gian duyệt"
    )
    verification_note = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Ghi chú khi duyệt"
    )

    class Meta:
        verbose_name = "Kết quả xét nghiệm"
        verbose_name_plural = "Các kết quả xét nghiệm"

    def __str__(self):
        return f"Result: {self.value_string} for {self.detail}"
    
    def save(self, *args, **kwargs):
        """Auto-flag abnormal results based on test limits"""
        if self.value_numeric is not None and self.detail and self.detail.test:
            test = self.detail.test
            
            # Check critical values first
            if test.panic_low is not None and self.value_numeric < test.panic_low:
                self.is_critical = True
                self.is_abnormal = True
                self.abnormal_flag = 'LL'
            elif test.panic_high is not None and self.value_numeric > test.panic_high:
                self.is_critical = True
                self.is_abnormal = True
                self.abnormal_flag = 'HH'
            # Then check normal range
            elif test.min_limit is not None and self.value_numeric < test.min_limit:
                self.is_abnormal = True
                self.abnormal_flag = 'L'
            elif test.max_limit is not None and self.value_numeric > test.max_limit:
                self.is_abnormal = True
                self.abnormal_flag = 'H'
            else:
                self.is_abnormal = False
                self.is_critical = False
                self.abnormal_flag = None
        
        super().save(*args, **kwargs)
