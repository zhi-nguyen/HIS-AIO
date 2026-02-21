from django.apps import AppConfig


class ReceptionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core_services.reception'

    def ready(self):
        import apps.core_services.reception.signals  # noqa: F401

