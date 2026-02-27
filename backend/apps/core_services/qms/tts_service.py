"""
TTS Service — Text-to-Speech Audio Generation for Patient Calling

This module provides Celery tasks to:
1. Generate Vietnamese TTS audio for patient announcements using edge-tts
2. Pre-generate audio for upcoming patients in the queue
3. Clean up old audio files daily

Audio files are stored in MEDIA_ROOT/audio/tts/ and cached in Redis.
"""

import os
import re
import logging
import asyncio
from pathlib import Path
from datetime import date, timedelta

from celery import shared_task
from django.conf import settings

import redis

logger = logging.getLogger(__name__)


def _get_redis_client():
    """Get a Redis client for TTS audio path caching."""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
    )


def _get_audio_dir() -> Path:
    """Get the TTS audio directory, creating it if needed."""
    audio_dir = Path(settings.MEDIA_ROOT) / settings.TTS_AUDIO_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)
    return audio_dir


def _sanitize_filename(name: str) -> str:
    """Sanitize a name for use in filenames."""
    # Replace Vietnamese chars and spaces  
    name = name.lower().strip()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[\s]+', '_', name)
    return name[:50]  # Limit length


def _get_station_label(station) -> str:
    """
    Get a human-readable Vietnamese label for the station type.
    Handles both station_type codes and station names.
    """
    from .models import StationType

    type_labels = {
        StationType.RECEPTION: 'quầy tiếp đón',
        StationType.TRIAGE: 'phòng phân luồng',
        StationType.DOCTOR: 'phòng khám',
        StationType.LIS: 'phòng xét nghiệm',
        StationType.RIS: 'phòng chẩn đoán hình ảnh',
        StationType.PHARMACY: 'nhà thuốc',
        StationType.CASHIER: 'quầy thu ngân',
    }

    label = type_labels.get(station.station_type, 'phòng')
    return f"{label} {station.name}"


def build_announcement_text(patient_name: str, daily_sequence: int, station) -> str:
    """
    Build the Vietnamese announcement sentence.

    Example output:
        "Mời bệnh nhân Nguyễn Văn A, số thứ tự 5, vào phòng khám Nội 1"
    """
    station_label = _get_station_label(station)
    return (
        f"Mời bệnh nhân {patient_name}, "
        f"số thứ tự {daily_sequence}, "
        f"vào {station_label}"
    )


def _run_tts(text: str, output_path: str, voice: str = 'vi-VN-HoaiMyNeural') -> None:
    """
    Run edge-tts to generate an MP3 file.
    edge-tts is async, so we run it in an event loop.
    """
    import edge_tts

    async def _generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_generate())
    finally:
        loop.close()


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def generate_tts_audio(self, entry_id: str) -> dict:
    """
    Celery task: Generate TTS audio for a specific QueueEntry.

    1. Load patient info from QueueEntry
    2. Build announcement text
    3. Generate MP3 via edge-tts
    4. Save file to disk
    5. Cache path in Redis (TTL 24h)

    Args:
        entry_id: UUID string of the QueueEntry

    Returns:
        dict with file_path and audio_url
    """
    from .models import QueueEntry

    try:
        entry = QueueEntry.objects.select_related(
            'queue_number',
            'queue_number__visit',
            'queue_number__visit__patient',
            'station',
        ).get(id=entry_id)
    except QueueEntry.DoesNotExist:
        logger.warning('[TTS] QueueEntry not found: %s', entry_id)
        return {'error': f'QueueEntry not found: {entry_id}'}

    patient = entry.queue_number.visit.patient
    patient_name = getattr(patient, 'full_name', None) or str(patient)
    daily_seq = entry.queue_number.daily_sequence
    station = entry.station

    # Check if already generated (Redis)
    r = _get_redis_client()
    redis_key = f'tts:audio:{entry_id}'
    cached = r.get(redis_key)
    if cached:
        logger.info('[TTS] Audio already cached for entry=%s', entry_id)
        return {'file_path': cached, 'audio_url': _file_to_url(cached)}

    # Build text
    text = build_announcement_text(patient_name, daily_seq, station)
    logger.info('[TTS] Generating: "%s"', text)

    # File path
    audio_dir = _get_audio_dir()
    safe_name = _sanitize_filename(patient_name)
    filename = f"call_{entry_id}_{safe_name}.mp3"
    file_path = str(audio_dir / filename)

    try:
        voice = getattr(settings, 'TTS_VOICE', 'vi-VN-HoaiMyNeural')
        _run_tts(text, file_path, voice)
    except Exception as exc:
        logger.error('[TTS] edge-tts failed for entry=%s: %s', entry_id, exc)
        raise self.retry(exc=exc)

    # Cache in Redis (TTL 24 hours)
    r.setex(redis_key, 86400, file_path)

    logger.info('[TTS] Generated audio: %s', file_path)
    return {'file_path': file_path, 'audio_url': _file_to_url(file_path)}


@shared_task
def pre_generate_for_upcoming(station_id: str) -> dict:
    """
    Celery task: Pre-generate TTS audio for the next N patients in the queue.

    This is triggered after a patient is called, so the next batch
    of announcements are ready before they're needed.

    Args:
        station_id: UUID string of the ServiceStation
    """
    from .models import ServiceStation, QueueEntry, QueueStatus

    try:
        station = ServiceStation.objects.get(id=station_id)
    except ServiceStation.DoesNotExist:
        logger.warning('[TTS] Station not found: %s', station_id)
        return {'error': f'Station not found: {station_id}'}

    count = settings.TTS_PRE_GENERATE_COUNT

    # Get next N waiting entries
    upcoming = QueueEntry.objects.filter(
        station=station,
        status=QueueStatus.WAITING,
    ).order_by('-priority', 'entered_queue_time')[:count]

    r = _get_redis_client()
    generated = 0
    skipped = 0

    for entry in upcoming:
        redis_key = f'tts:audio:{entry.id}'
        if r.exists(redis_key):
            skipped += 1
            continue
        # Dispatch individual generation task
        generate_tts_audio.delay(str(entry.id))
        generated += 1

    logger.info(
        '[TTS] Pre-generate for station=%s: dispatched=%d, skipped=%d',
        station.code, generated, skipped,
    )
    return {'station': station.code, 'generated': generated, 'skipped': skipped}


@shared_task
def cleanup_old_audio() -> dict:
    """
    Celery Beat task: Delete TTS audio files older than 1 day.
    Runs daily at 23:59 (configured in config/celery.py).
    """
    import time

    audio_dir = _get_audio_dir()
    cutoff = time.time() - 86400  # 24 hours ago

    deleted = 0
    errors = 0

    for f in audio_dir.glob('call_*.mp3'):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        except Exception as exc:
            logger.error('[TTS] Failed to delete %s: %s', f, exc)
            errors += 1

    # Also flush old Redis keys (they have TTL, but clean up anyway)
    r = _get_redis_client()
    cursor = 0
    flushed = 0
    while True:
        cursor, keys = r.scan(cursor, match='tts:audio:*', count=100)
        for key in keys:
            path = r.get(key)
            if path and not os.path.exists(path):
                r.delete(key)
                flushed += 1
        if cursor == 0:
            break

    logger.info(
        '[TTS] Cleanup: deleted=%d files, flushed=%d Redis keys, errors=%d',
        deleted, flushed, errors,
    )
    return {'deleted': deleted, 'flushed': flushed, 'errors': errors}


def get_audio_url(entry_id: str) -> str | None:
    """
    Get the audio URL for a QueueEntry from Redis cache.

    Returns:
        URL string or None if not cached
    """
    r = _get_redis_client()
    redis_key = f'tts:audio:{entry_id}'
    file_path = r.get(redis_key)

    if file_path and os.path.exists(file_path):
        return _file_to_url(file_path)

    return None


def _file_to_url(file_path: str) -> str:
    """Convert an absolute file path to a media URL."""
    media_root = str(settings.MEDIA_ROOT)
    relative = file_path.replace(media_root, '').replace('\\', '/').lstrip('/')
    return f"{settings.MEDIA_URL}{relative}"
