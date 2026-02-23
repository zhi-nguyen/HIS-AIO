"""
DICOM Web Client — wrapper cho giao tiếp với PACS Server qua DICOMweb.

Hỗ trợ:
- QIDO-RS: Query (tìm kiếm Studies)
- WADO-RS: Retrieve (lấy metadata + ảnh)
- STOW-RS: Store (upload DICOM instances)

Khi INTEROP_MOCK_MODE=True, trả về mock data để test.
"""

import logging
import time
from typing import Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class DICOMWebClient:
    """
    Client wrapper cho DICOMweb API (QIDO-RS, WADO-RS, STOW-RS).

    Usage:
        from apps.interoperability.dicom.client import DICOMWebClient

        client = DICOMWebClient.from_config()  # Load from PACSConfig
        studies = client.query_studies(patient_id='BN001')
    """

    def __init__(
        self,
        base_url: str,
        qido_path: str = '/qido-rs',
        wado_path: str = '/wado-rs',
        stow_path: str = '/stow-rs',
        auth_headers: Optional[dict] = None,
        timeout: int = 60,
        mock_mode: bool = True,
    ):
        self.base_url = base_url.rstrip('/')
        self.qido_url = f'{self.base_url}{qido_path}'
        self.wado_url = f'{self.base_url}{wado_path}'
        self.stow_url = f'{self.base_url}{stow_path}'
        self.auth_headers = auth_headers or {}
        self.timeout = timeout
        self.mock_mode = mock_mode

    @classmethod
    def from_config(cls, config=None) -> 'DICOMWebClient':
        """
        Create client from PACSConfig model instance.
        Falls back to mock mode if no config or settings indicate mock.
        """
        mock_mode = getattr(settings, 'INTEROP_MOCK_MODE', True)

        if config is None:
            from apps.interoperability.models import PACSConfig
            config = PACSConfig.objects.filter(is_active=True).first()

        if config is None:
            logger.warning("No active PACSConfig found, using mock mode")
            return cls(
                base_url='http://mock-pacs.local',
                mock_mode=True,
            )

        auth_headers = {}
        if config.auth_type == 'BEARER' and config.auth_token:
            auth_headers['Authorization'] = f'Bearer {config.auth_token}'
        elif config.auth_type == 'BASIC' and config.auth_token:
            auth_headers['Authorization'] = f'Basic {config.auth_token}'

        return cls(
            base_url=config.base_url,
            qido_path=config.qido_rs_path,
            wado_path=config.wado_rs_path,
            stow_path=config.stow_rs_path,
            auth_headers=auth_headers,
            timeout=config.timeout_seconds,
            mock_mode=mock_mode,
        )

    # ─── QIDO-RS: Query Studies ──────────────────────────────────────────────

    def query_studies(
        self,
        patient_id: Optional[str] = None,
        patient_name: Optional[str] = None,
        study_date: Optional[str] = None,
        modality: Optional[str] = None,
        accession_number: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """
        QIDO-RS: Search for studies.

        Args:
            patient_id: Patient ID to filter by
            patient_name: Patient name (partial match)
            study_date: Date range (YYYYMMDD or YYYYMMDD-YYYYMMDD)
            modality: Modality code (CT, MR, US, etc.)
            accession_number: Accession number
            limit: Max results
            offset: Pagination offset

        Returns:
            list[dict]: List of study metadata
        """
        if self.mock_mode:
            return self._mock_query_studies(patient_id)

        params = {
            'limit': limit,
            'offset': offset,
        }
        if patient_id:
            params['PatientID'] = patient_id
        if patient_name:
            params['PatientName'] = patient_name
        if study_date:
            params['StudyDate'] = study_date
        if modality:
            params['ModalitiesInStudy'] = modality
        if accession_number:
            params['AccessionNumber'] = accession_number

        url = f'{self.qido_url}/studies'

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    url,
                    params=params,
                    headers={
                        'Accept': 'application/dicom+json',
                        **self.auth_headers,
                    },
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"QIDO-RS query failed: {e}")
            return []

    # ─── WADO-RS: Retrieve Study Metadata ────────────────────────────────────

    def retrieve_study(self, study_uid: str) -> Optional[dict]:
        """
        WADO-RS: Retrieve study metadata.

        Args:
            study_uid: DICOM Study Instance UID

        Returns:
            dict: Study metadata or None if not found
        """
        if self.mock_mode:
            return self._mock_retrieve_study(study_uid)

        url = f'{self.wado_url}/studies/{study_uid}/metadata'

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    url,
                    headers={
                        'Accept': 'application/dicom+json',
                        **self.auth_headers,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data[0] if data else None
        except httpx.HTTPError as e:
            logger.error(f"WADO-RS retrieve failed for {study_uid}: {e}")
            return None

    def get_study_thumbnail_url(self, study_uid: str, series_uid: str = None) -> str:
        """
        Get thumbnail URL for a study/series via WADO-RS.

        Returns a URL that can be used directly in <img> tags.
        """
        if series_uid:
            return (
                f'{self.wado_url}/studies/{study_uid}'
                f'/series/{series_uid}/thumbnail'
            )
        return f'{self.wado_url}/studies/{study_uid}/thumbnail'

    # ─── STOW-RS: Store DICOM Instance ───────────────────────────────────────

    def store_instance(self, dicom_bytes: bytes) -> dict:
        """
        STOW-RS: Upload a DICOM instance to PACS.

        Args:
            dicom_bytes: Raw DICOM file content

        Returns:
            dict: Store response with status
        """
        if self.mock_mode:
            return self._mock_store_instance()

        url = f'{self.stow_url}/studies'

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    content=dicom_bytes,
                    headers={
                        'Content-Type': 'application/dicom',
                        'Accept': 'application/dicom+json',
                        **self.auth_headers,
                    },
                )
                response.raise_for_status()
                return {
                    'status': 'success',
                    'response': response.json() if response.content else {},
                }
        except httpx.HTTPError as e:
            logger.error(f"STOW-RS store failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
            }

    # ─── Mock Data ───────────────────────────────────────────────────────────

    def _mock_query_studies(self, patient_id: Optional[str] = None) -> list[dict]:
        """Return mock QIDO-RS response."""
        return [
            {
                '0020000D': {'vr': 'UI', 'Value': ['1.2.840.113619.2.55.3.1234567890.1']},
                '00080020': {'vr': 'DA', 'Value': ['20260223']},
                '00080050': {'vr': 'SH', 'Value': ['ACC001']},
                '00080061': {'vr': 'CS', 'Value': ['CT']},
                '00100010': {'vr': 'PN', 'Value': [{'Alphabetic': 'NGUYEN^VAN A'}]},
                '00100020': {'vr': 'LO', 'Value': [patient_id or 'BN001']},
                '00080060': {'vr': 'CS', 'Value': ['CT']},
                '_description': 'CT Ngực (mock)',
            },
            {
                '0020000D': {'vr': 'UI', 'Value': ['1.2.840.113619.2.55.3.1234567890.2']},
                '00080020': {'vr': 'DA', 'Value': ['20260222']},
                '00080050': {'vr': 'SH', 'Value': ['ACC002']},
                '00080061': {'vr': 'CS', 'Value': ['MR']},
                '00100010': {'vr': 'PN', 'Value': [{'Alphabetic': 'NGUYEN^VAN A'}]},
                '00100020': {'vr': 'LO', 'Value': [patient_id or 'BN001']},
                '00080060': {'vr': 'CS', 'Value': ['MR']},
                '_description': 'MRI Sọ não (mock)',
            },
        ]

    def _mock_retrieve_study(self, study_uid: str) -> dict:
        """Return mock WADO-RS study metadata."""
        return {
            '0020000D': {'vr': 'UI', 'Value': [study_uid]},
            '00080020': {'vr': 'DA', 'Value': ['20260223']},
            '00080030': {'vr': 'TM', 'Value': ['143000']},
            '00080050': {'vr': 'SH', 'Value': ['ACC001']},
            '00080060': {'vr': 'CS', 'Value': ['CT']},
            '00081030': {'vr': 'LO', 'Value': ['CT CHEST']},
            '00100010': {'vr': 'PN', 'Value': [{'Alphabetic': 'NGUYEN^VAN A'}]},
            '00100020': {'vr': 'LO', 'Value': ['BN001']},
            '00201206': {'vr': 'IS', 'Value': ['1']},  # Number of Series
            '00201208': {'vr': 'IS', 'Value': ['120']},  # Number of Instances
            '_mock': True,
        }

    def _mock_store_instance(self) -> dict:
        """Return mock STOW-RS response."""
        return {
            'status': 'success',
            'mock': True,
            'message': 'DICOM instance stored (mock mode)',
            'study_uid': '1.2.840.113619.2.55.3.1234567890.999',
        }
