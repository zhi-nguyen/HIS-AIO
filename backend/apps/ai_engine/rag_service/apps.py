"""
Django App Config for RAG Service

Đăng ký signals cho auto-indexing ClinicalRecord.
"""

from django.apps import AppConfig


class RagServiceConfig(AppConfig):
    """Django app config cho RAG Service."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_engine.rag_service'
    verbose_name = 'RAG Service'
    
    def ready(self):
        """
        Đăng ký signals khi app khởi động.
        
        Import signals module để kích hoạt các signal handlers.
        """
        # Import signals to register handlers
        from . import signals  # noqa: F401
