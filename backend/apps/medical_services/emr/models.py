from django.db import models

from apps.core_services.core.models import UUIDModel, ICD10Code

class ClinicalRecord(UUIDModel):
    visit = models.OneToOneField(
        'reception.Visit',
        on_delete=models.CASCADE,
        related_name='clinical_record'
    )
    
    doctor = models.ForeignKey(
        'authentication.Staff',
        on_delete=models.PROTECT,
        related_name='clinical_records',
        null=True, blank=True
    )
    
    # Dữ liệu chuyên môn nằm hết ở đây
    chief_complaint = models.TextField(help_text="Lý do vào viện/Triệu chứng chính")
    history_of_present_illness = models.TextField(help_text="Bệnh sử", null=True, blank=True)
    
    # Phần khám
    physical_exam = models.TextField(help_text="Khám lâm sàng", null=True, blank=True)

    vital_signs = models.JSONField(null=True, blank=True)

    triage_agent_summary = models.JSONField(null=True, blank=True)
    clinical_agent_summary = models.JSONField(null=True, blank=True)
    core_agent_summary = models.JSONField(null=True, blank=True)

    # Thêm field theo Phase 1 - AI Outpatient
    ai_suggestion_json = models.JSONField(verbose_name="Gợi ý thô từ AI", null=True, blank=True)
    is_finalized = models.BooleanField(default=False, verbose_name="Đã hoàn tất khám")

    medical_summary = models.TextField(null=True, blank=True) #Bác sĩ tự viết tóm tắt bệnh án nếu cần
    
    final_diagnosis = models.TextField(null=True, blank=True)

    main_icd = models.ForeignKey(
        ICD10Code,
        on_delete=models.PROTECT,
        related_name='main_records',
        verbose_name="Bệnh chính (ICD-10)",
        null=True, blank=True
    )

    sub_icds = models.ManyToManyField(
        ICD10Code,
        blank=True,
        related_name='sub_records',
        verbose_name="Bệnh kèm theo"
    )

    treatment_plan = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Medical Record for {self.visit.visit_code}"

