from django.db import models
from apps.core_services.core.models import UUIDModel

class AgentProfile(UUIDModel):
    class Role(models.TextChoices):
        CONSULTANT = 'CONSULTANT', 'Consultant'
        TRIAGE = 'TRIAGE', 'Triage'
        CLINICAL = 'CLINICAL', 'Clinical'
        PHARMACY = 'PHARMACY', 'Pharmacy'
        PARACLINICAL = 'PARACLINICAL', 'Paraclinical'
        MARKETING = 'MARKETING', 'Marketing'
        HUMAN_INTERVENTION = 'HUMAN_INTERVENTION', 'Human Intervention'
        CORE = 'CORE', 'Core'
        
    class ModelName(models.TextChoices):
        # Thêm model mới vào đây nếu muốn hiển thị trong Django Admin dropdown
        GEMINI_2_5_PRO  = 'gemini-2.5-pro',   'Gemini 2.5 Pro'
        GEMINI_2_0_FLASH= 'gemini-2.0-flash',  'Gemini 2.0 Flash'
        GEMINI_1_5_PRO  = 'gemini-1.5-pro',   'Gemini 1.5 Pro'
        GEMINI_1_5_FLASH= 'gemini-1.5-flash',  'Gemini 1.5 Flash'

    @staticmethod
    def _default_model():
        """Runtime default: đọc từ AGENT_DEFAULT_MODEL trong .env."""
        from django.conf import settings
        return getattr(settings, 'AGENT_DEFAULT_MODEL', 'gemini-2.0-flash')

    name = models.CharField(max_length=100, help_text="Tên định danh của Agent (VD: Bác sĩ AI Khoa Nhi)")
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CORE
    )
    model_name = models.CharField(
        max_length=50,  # Tăng từ 30 → 50 cho tên model dài hơn
        choices=ModelName.choices,
        default=_default_model.__func__,  # Đọc từ settings/.env lúc runtime
    )
    temperature = models.FloatField(default=0.7, help_text="Độ sáng tạo (0.0 - 1.0)")
    system_instructions = models.TextField(blank=True, help_text="Prompt hướng dẫn hành vi cốt lõi")

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

class VectorStore(UUIDModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    collection_name = models.CharField(max_length=150, unique=True)
    
    # Configuration
    embedding_model = models.CharField(
        max_length=100, 
        default='',
        help_text="Tên model (VD: )"
    )
    dimensions = models.IntegerField(
        default=768,
        help_text="Kích thước vector (VD: 768)"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @classmethod
    def get_active_config(cls):
        """Get the first active configuration or None."""
        return cls.objects.filter(is_active=True).first()
    
class AgentLog(UUIDModel):
    agent = models.ForeignKey(
        AgentProfile,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    vector = models.ForeignKey(
        VectorStore,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_logs'
    )
    action = models.TextField(help_text="Mô tả hành động hoặc User Query")
    input_token = models.IntegerField(default=0)
    output_token = models.IntegerField(default=0)
    latency = models.FloatField(help_text="Thời gian phản hồi (giây)")

    def __str__(self):
        return f"Log: {self.agent.name} | {self.created_at.strftime('%Y-%m-%d %H:%M')}"