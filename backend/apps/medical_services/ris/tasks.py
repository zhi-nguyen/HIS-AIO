"""
Celery Tasks cho RIS — Xử lý bất đồng bộ dữ liệu DICOM từ Orthanc.
"""
import logging
import requests
from django.conf import settings
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# URL Orthanc REST API — lấy từ settings hoặc default
ORTHANC_URL = getattr(settings, 'ORTHANC_URL', 'http://orthanc:8042')
ORTHANC_USER = getattr(settings, 'ORTHANC_USER', 'his_backend')
ORTHANC_PASSWORD = getattr(settings, 'ORTHANC_PASSWORD', 'his_backend_secret')


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_dicom_study(
    self,
    study_uid,
    orthanc_id,
    accession_number='',
    patient_id='',
    patient_name='',
    study_description='',
    number_of_series=0,
):
    """
    Celery task xử lý khi Orthanc gửi webhook (OnStableStudy).

    Luồng:
    1. Gọi Orthanc REST API lấy metadata chi tiết (nếu cần)
    2. Tìm ImagingOrder khớp accession_number
    3. Tạo/cập nhật ImagingExecution với dicom_study_uid
    4. Cập nhật status → COMPLETED (đã chụp, chờ đọc)
    5. Bắn WebSocket event thông báo BS CĐHA
    """
    from .models import ImagingOrder, ImagingExecution

    logger.info(
        f"[Celery] process_dicom_study: study_uid={study_uid}, "
        f"accession={accession_number}, orthanc_id={orthanc_id}"
    )

    # ------------------------------------------------------------------
    # Bước 1: Gọi Orthanc REST API lấy thêm thông tin (tuỳ chọn)
    # ------------------------------------------------------------------
    orthanc_metadata = None
    if orthanc_id:
        try:
            resp = requests.get(
                f"{ORTHANC_URL}/studies/{orthanc_id}",
                auth=(ORTHANC_USER, ORTHANC_PASSWORD),
                timeout=10,
            )
            if resp.status_code == 200:
                orthanc_metadata = resp.json()
                logger.info(f"[Celery] Orthanc metadata retrieved for {orthanc_id}")
            else:
                logger.warning(
                    f"[Celery] Orthanc API returned {resp.status_code} for {orthanc_id}"
                )
        except requests.RequestException as e:
            logger.error(f"[Celery] Failed to call Orthanc API: {e}")

    # ------------------------------------------------------------------
    # Bước 2: Tìm ImagingOrder khớp accession_number
    # ------------------------------------------------------------------
    order = None

    if accession_number:
        try:
            order = ImagingOrder.objects.get(accession_number=accession_number)
            logger.info(f"[Celery] Found ImagingOrder by accession_number: {order.id}")
        except ImagingOrder.DoesNotExist:
            logger.warning(
                f"[Celery] No ImagingOrder found for accession_number={accession_number}"
            )
        except ImagingOrder.MultipleObjectsReturned:
            logger.error(
                f"[Celery] Multiple ImagingOrders for accession_number={accession_number}"
            )

    if order is None:
        logger.info(
            f"[Celery] Study {study_uid} received but no matching order found. "
            f"Will be matched manually."
        )
        return {
            'status': 'unmatched',
            'study_uid': study_uid,
            'accession_number': accession_number,
        }

    # ------------------------------------------------------------------
    # Bước 3: Tạo/cập nhật ImagingExecution
    # ------------------------------------------------------------------
    # Cố gắng lấy instance_id đầu tiên/giữa từ Orthanc để làm preview
    instance_id_for_preview = None
    if orthanc_id:
        try:
            instances_resp = requests.get(
                f"{ORTHANC_URL}/studies/{orthanc_id}/instances",
                auth=(ORTHANC_USER, ORTHANC_PASSWORD),
                timeout=10,
            )
            if instances_resp.status_code == 200:
                instances = instances_resp.json()
                if instances and isinstance(instances, list) and len(instances) > 0:
                    # Lấy ảnh ở giữa (cho an toàn nếu chụp nhiều slice) hoặc ảnh đầu tiên
                    mid_idx = len(instances) // 2
                    instance_id_for_preview = instances[mid_idx].get("ID")
                    logger.info(f"[Celery] Found instance for preview: {instance_id_for_preview}")
        except Exception as e:
            logger.error(f"[Celery] Failed to get instances for preview: {e}")

    execution, exec_created = ImagingExecution.objects.update_or_create(
        order=order,
        defaults={
            'dicom_study_uid': study_uid,
            'orthanc_instance_id': instance_id_for_preview,
            'execution_note': f"Auto-matched from PACS. Description: {study_description}",
        }
    )

    if exec_created:
        logger.info(f"[Celery] Created ImagingExecution for order {order.id}")
    else:
        logger.info(f"[Celery] Updated ImagingExecution for order {order.id}")

    # ------------------------------------------------------------------
    # Bước 4: Cập nhật status → COMPLETED (đã chụp, chờ đọc)
    # ------------------------------------------------------------------
    if order.status in [
        ImagingOrder.Status.PENDING,
        ImagingOrder.Status.SCHEDULED,
        ImagingOrder.Status.IN_PROGRESS,
    ]:
        order.status = ImagingOrder.Status.COMPLETED
        order.save()  # Triggers post_save signal → WebSocket
        logger.info(f"[Celery] Order {order.id} status updated to COMPLETED")

    # ------------------------------------------------------------------
    # Bước 5: Bắn thêm WebSocket event chi tiết (NEW_STUDY)
    # ------------------------------------------------------------------
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "ris_updates",
                {
                    "type": "ris.new_study",
                    "order_id": str(order.id),
                    "study_uid": study_uid,
                    "accession_number": accession_number,
                    "patient_name": patient_name,
                    "study_description": study_description,
                }
            )
            logger.info(f"[Celery] WebSocket NEW_STUDY event sent for order {order.id}")
    except Exception as e:
        logger.error(f"[Celery] Failed to send WebSocket event: {e}")

    return {
        'status': 'matched',
        'order_id': str(order.id),
        'study_uid': study_uid,
    }
