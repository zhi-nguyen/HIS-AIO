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
        related_name='clinical_records'
    )
    
    # Dữ liệu chuyên môn nằm hết ở đây
    chief_complaint = models.TextField(help_text="Lý do vào viện/Triệu chứng chính")
    history_of_present_illness = models.TextField(help_text="Bệnh sử")
    
    # Phần khám
    physical_exam = models.TextField(help_text="Khám lâm sàng")

    vital_signs = models.JSONField(null=True, blank=True)

    triage_agent_summary = models.JSONField(null=True, blank=True)
    clinical_agent_summary = models.JSONField(null=True, blank=True)
    core_agent_summary = models.JSONField(null=True, blank=True)

    medical_summary = models.TextField(null=True, blank=True) #Bác sĩ tự viết tóm tắt bệnh án nếu cần
    
    final_diagnosis = models.TextField()

    main_icd = models.ForeignKey(
        ICD10Code,
        on_delete=models.PROTECT,
        related_name='main_records',
        verbose_name="Bệnh chính (ICD-10)"
    )

    sub_icds = models.ManyToManyField(
        ICD10Code,
        blank=True,
        related_name='sub_records',
        verbose_name="Bệnh kèm theo"
    )

    treatment_plan = models.TextField()

    def __str__(self):
        return f"Medical Record for {self.visit.visit_code}"

