"""
Celery tasks proxy for QMS app.

autodiscover_tasks() only imports 'tasks.py'. This file re-exports
the actual TTS tasks from tts_service.py so Celery workers can find them.
"""

from .tts_service import (  # noqa: F401
    generate_tts_audio,
    pre_generate_for_upcoming,
    cleanup_old_audio,
)
