"""
Celery configuration for HIS project.

Uses Redis as both broker and result backend.
Auto-discovers tasks from all installed Django apps.
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('his')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in all INSTALLED_APPS
app.autodiscover_tasks()

# Explicitly register tts_service module (not named tasks.py)
app.autodiscover_tasks(
    ['apps.core_services.qms'],
    related_name='tts_service',
)

# Celery Beat schedule
app.conf.beat_schedule = {
    'cleanup-tts-audio-daily': {
        'task': 'apps.core_services.qms.tts_service.cleanup_old_audio',
        'schedule': crontab(hour=23, minute=59),
        'args': (),
    },
}
