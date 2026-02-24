"""
WADO-RS Proxy — proxy requests từ HIS frontend đến PACS server.

Cho phép frontend truy cập ảnh DICOM qua HIS API mà không cần
kết nối trực tiếp đến PACS (bảo mật + CORS).
"""

import logging
from typing import Optional

from .client import DICOMWebClient

logger = logging.getLogger(__name__)


def get_study_image_urls(
    study_uid: str,
    pacs_config=None,
) -> dict:
    """
    Lấy danh sách URL ảnh của một study từ PACS.

    Args:
        study_uid: DICOM Study Instance UID
        pacs_config: PACSConfig instance (optional, auto-detect if None)

    Returns:
        dict with study metadata and image URLs
    """
    client = DICOMWebClient.from_config(pacs_config)
    metadata = client.retrieve_study(study_uid)

    if not metadata:
        return {
            'study_uid': study_uid,
            'found': False,
            'images': [],
        }

    # Build thumbnail URL
    thumbnail_url = client.get_study_thumbnail_url(study_uid)

    return {
        'study_uid': study_uid,
        'found': True,
        'metadata': metadata,
        'thumbnail_url': thumbnail_url,
        'wado_retrieve_url': f'{client.wado_url}/studies/{study_uid}',
    }


def link_imaging_order_to_pacs(
    imaging_order,
    study_uid: str,
    pacs_config=None,
) -> bool:
    """
    Liên kết ImagingOrder với Study UID từ PACS.
    Cập nhật execution record với WADO-RS URL.

    Args:
        imaging_order: ImagingOrder instance
        study_uid: DICOM Study Instance UID
        pacs_config: PACSConfig instance

    Returns:
        bool: True if linked successfully
    """
    client = DICOMWebClient.from_config(pacs_config)

    # Verify study exists
    metadata = client.retrieve_study(study_uid)
    if not metadata:
        logger.warning(f"Study {study_uid} not found in PACS")
        return False

    # Update execution with WADO URL
    if hasattr(imaging_order, 'execution') and imaging_order.execution:
        execution = imaging_order.execution
        thumbnail_url = client.get_study_thumbnail_url(study_uid)
        execution.preview_image_url = thumbnail_url
        execution.save(update_fields=['preview_image_url'])
        logger.info(
            f"Linked ImagingOrder {imaging_order.id} to Study {study_uid}"
        )
        return True

    logger.warning(f"ImagingOrder {imaging_order.id} has no execution record")
    return False
