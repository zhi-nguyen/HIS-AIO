"""
Patient Context Retrieval for RAG

Retrieves and aggregates patient information for LLM context including:
- Demographics
- Clinical record history (semantic search)
- Current prescriptions
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async

from .vector_service import VectorService
from .embeddings import EmbeddingService
from .pii_masking import mask_patient_id, mask_sensitive_fields

logger = logging.getLogger(__name__)


async def retrieve_patient_context(
    patient_id: str,
    query: Optional[str] = None,
    top_k_records: int = 5,
    vector_service: Optional[VectorService] = None,
    embedding_service: Optional[EmbeddingService] = None
) -> Dict[str, Any]:
    """
    Retrieve comprehensive patient context for LLM.
    
    Args:
        patient_id: Patient UUID
        query: Optional query for semantic search of clinical records
        top_k_records: Number of clinical records to retrieve
        vector_service: VectorService instance (creates new if None)
        embedding_service: EmbeddingService instance (creates new if None)
        
    Returns:
        Dictionary with patient context including demographics, clinical history, and prescriptions
    """
    try:
        logger.info(f"Retrieving context for patient: {mask_patient_id(patient_id)}")
        
        # Initialize services if not provided
        if vector_service is None:
            vector_service = VectorService()
        if embedding_service is None:
            embedding_service = EmbeddingService()
        
        # Fetch patient demographics
        demographics = await _get_patient_demographics(patient_id)
        
        # Fetch clinical records (semantic search if query provided, otherwise most recent)
        clinical_records = await _get_clinical_records(
            patient_id=patient_id,
            query=query,
            top_k=top_k_records,
            vector_service=vector_service,
            embedding_service=embedding_service
        )
        
        # Fetch current prescriptions (if available)
        prescriptions = await _get_current_prescriptions(patient_id)
        
        # Aggregate context
        context = {
            'patient_id': patient_id,
            'demographics': demographics,
            'clinical_history': clinical_records,
            'current_prescriptions': prescriptions,
            'retrieved_at': datetime.now().isoformat()
        }
        
        logger.info(f"Retrieved context with {len(clinical_records)} clinical records for patient {mask_patient_id(patient_id)}")
        
        return context
        
    except Exception as e:
        logger.error(f"Error retrieving patient context: {e}")
        raise


async def _get_patient_demographics(patient_id: str) -> Dict[str, Any]:
    """
    Fetch patient demographic information.
    
    Args:
        patient_id: Patient UUID
        
    Returns:
        Dictionary with demographic data
    """
    from apps.core_services.patients.models import Patient
    
    @sync_to_async
    def _fetch_patient():
        try:
            patient = Patient.objects.get(id=patient_id)
            
            # Calculate age
            age = None
            if patient.date_of_birth:
                today = datetime.now().date()
                age = today.year - patient.date_of_birth.year
                if today.month < patient.date_of_birth.month or \
                   (today.month == patient.date_of_birth.month and today.day < patient.date_of_birth.day):
                    age -= 1
            
            return {
                'patient_code': patient.patient_code,
                'full_name': patient.full_name,
                'age': age,
                'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                'gender': patient.get_gender_display(),
                'gender_code': patient.gender,
                'address': patient.full_address,
                'contact_number': patient.contact_number,
                'insurance_number': patient.insurance_number,
            }
            
        except Patient.DoesNotExist:
            logger.error(f"Patient not found: {mask_patient_id(patient_id)}")
            return {}
    
    return await _fetch_patient()


async def _get_clinical_records(
    patient_id: str,
    query: Optional[str],
    top_k: int,
    vector_service: VectorService,
    embedding_service: EmbeddingService
) -> List[Dict[str, Any]]:
    """
    Fetch clinical records using semantic search or recency.
    
    Args:
        patient_id: Patient UUID
        query: Optional query for semantic search
        top_k: Number of records to retrieve
        vector_service: VectorService instance
        embedding_service: EmbeddingService instance
        
    Returns:
        List of clinical record summaries
    """
    from apps.medical_services.emr.models import ClinicalRecord
    
    if query:
        # Semantic search
        return await _semantic_search_clinical_records(
            patient_id=patient_id,
            query=query,
            top_k=top_k,
            vector_service=vector_service,
            embedding_service=embedding_service
        )
    else:
        # Fetch most recent records
        return await _get_recent_clinical_records(patient_id=patient_id, top_k=top_k)


async def _semantic_search_clinical_records(
    patient_id: str,
    query: str,
    top_k: int,
    vector_service: VectorService,
    embedding_service: EmbeddingService
) -> List[Dict[str, Any]]:
    """
    Search clinical records using semantic similarity.
    
    Args:
        patient_id: Patient UUID
        query: Search query
        top_k: Number of results
        vector_service: VectorService instance
        embedding_service: EmbeddingService instance
        
    Returns:
        List of relevant clinical records
    """
    try:
        # Generate query embedding
        query_embedding = await embedding_service.embed_text(query)
        
        # Search in clinical records collection
        results = await vector_service.semantic_search(
            collection_name='clinical_records',
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Fetch more for filtering
            where={'patient_id': patient_id}  # Filter by patient
        )
        
        # Format results
        formatted_records = []
        for result in results[:top_k]:
            metadata = result.get('metadata', {})
            formatted_records.append({
                'record_id': result['id'],
                'visit_code': metadata.get('visit_code'),
                'date': metadata.get('created_at'),
                'chief_complaint': metadata.get('chief_complaint'),
                'diagnosis': metadata.get('diagnosis'),
                'icd_code': metadata.get('main_icd_code'),
                'similarity_score': result.get('similarity'),
                'summary': result.get('document')
            })
        
        return formatted_records
        
    except Exception as e:
        logger.warning(f"Semantic search failed, falling back to recent records: {e}")
        return await _get_recent_clinical_records(patient_id=patient_id, top_k=top_k)


async def _get_recent_clinical_records(patient_id: str, top_k: int) -> List[Dict[str, Any]]:
    """
    Fetch most recent clinical records.
    
    Args:
        patient_id: Patient UUID
        top_k: Number of records to retrieve
        
    Returns:
        List of recent clinical records
    """
    from apps.medical_services.emr.models import ClinicalRecord
    
    @sync_to_async
    def _fetch_records():
        try:
            records = ClinicalRecord.objects.filter(
                visit__patient_id=patient_id
            ).select_related(
                'visit', 'main_icd', 'doctor'
            ).order_by('-created_at')[:top_k]
            
            formatted_records = []
            for record in records:
                formatted_records.append({
                    'record_id': str(record.id),
                    'visit_code': record.visit.visit_code,
                    'date': record.created_at.isoformat(),
                    'chief_complaint': record.chief_complaint,
                    'physical_exam': record.physical_exam,
                    'diagnosis': record.final_diagnosis,
                    'icd_code': record.main_icd.code if record.main_icd else None,
                    'icd_name': record.main_icd.name if record.main_icd else None,
                    'doctor': record.doctor.user.get_full_name() if record.doctor else None,
                    'treatment_plan': record.treatment_plan
                })
            
            return formatted_records
            
        except Exception as e:
            logger.error(f"Error fetching clinical records: {e}")
            return []
    
    return await _fetch_records()


async def _get_current_prescriptions(patient_id: str) -> List[Dict[str, Any]]:
    """
    Fetch current prescriptions for patient.
    
    Note: This is a placeholder as prescription models were not found in the codebase.
    
    Args:
        patient_id: Patient UUID
        
    Returns:
        List of current prescriptions
    """
    # TODO: Implement when prescription models are available
    logger.debug(f"Prescription retrieval not implemented for patient {mask_patient_id(patient_id)}")
    return []


def format_context_for_llm(context: Dict[str, Any], include_pii: bool = True) -> str:
    """
    Format patient context into LLM-friendly string.
    
    Args:
        context: Patient context dictionary from retrieve_patient_context
        include_pii: Whether to include PII (set False for logging)
        
    Returns:
        Formatted context string
    """
    demographics = context.get('demographics', {})
    clinical_history = context.get('clinical_history', [])
    prescriptions = context.get('current_prescriptions', [])
    
    # Mask PII if requested
    if not include_pii:
        demographics = mask_sensitive_fields(demographics)
    
    # Format demographics
    age_text = f"{demographics.get('age')} tuổi" if demographics.get('age') else "Không rõ tuổi"
    gender_text = demographics.get('gender', 'Không rõ')
    
    formatted = f"""
THÔNG TIN BỆNH NHÂN:
- Mã bệnh nhân: {demographics.get('patient_code', 'N/A')}
- Họ tên: {demographics.get('full_name', 'N/A')}
- Tuổi: {age_text}
- Giới tính: {gender_text}
- Địa chỉ: {demographics.get('address', 'Không có thông tin')}

LỊCH SỬ KHÁM BỆNH ({len(clinical_history)} lần khám gần nhất):
"""
    
    # Format clinical history
    for i, record in enumerate(clinical_history, 1):
        formatted += f"""
{i}. Ngày khám: {record.get('date', 'N/A')}
   - Mã khám: {record.get('visit_code', 'N/A')}
   - Lý do khám: {record.get('chief_complaint', 'N/A')}
   - Chẩn đoán: {record.get('diagnosis', 'N/A')}
   - Mã ICD-10: {record.get('icd_code', 'N/A')} - {record.get('icd_name', '')}
   - Phương án điều trị: {record.get('treatment_plan', 'N/A')}
"""
    
    # Format prescriptions
    if prescriptions:
        formatted += f"\n\nĐƠN THUỐC HIỆN TẠI ({len(prescriptions)} loại):\n"
        for i, prescription in enumerate(prescriptions, 1):
            formatted += f"{i}. {prescription}\n"
    else:
        formatted += "\n\nĐƠN THUỐC HIỆN TẠI: Không có thông tin\n"
    
    return formatted.strip()
