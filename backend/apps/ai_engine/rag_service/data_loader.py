"""
Data Loader for RAG Vector Database

Utilities to load clinical records and ICD-10 codes into vector database.
Supports initial loading and incremental updates.
"""

import logging
from typing import List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async

from .vector_service import VectorService
from .embeddings import EmbeddingService, embed_clinical_note, embed_icd10_code, embed_department
from .pii_masking import mask_patient_id

logger = logging.getLogger(__name__)


async def load_clinical_records_to_vector_db(
    batch_size: int = 100,
    vector_service: Optional[VectorService] = None,
    embedding_service: Optional[EmbeddingService] = None,
    since_date: Optional[datetime] = None
) -> int:
    """
    Load clinical records into vector database.
    
    Args:
        batch_size: Number of records to process per batch
        vector_service: VectorService instance (creates new if None)
        embedding_service: EmbeddingService instance (creates new if None)
        since_date: Only load records created/updated after this date (for incremental updates)
        
    Returns:
        Number of records loaded
    """
    from apps.medical_services.emr.models import ClinicalRecord
    
    logger.info(f"Starting clinical records loading (batch_size={batch_size}, since={since_date})")
    
    # Initialize services
    if vector_service is None:
        vector_service = VectorService()
    if embedding_service is None:
        embedding_service = EmbeddingService()
    
    # Get records to load
    @sync_to_async
    def _get_records():
        queryset = ClinicalRecord.objects.select_related(
            'visit__patient', 'main_icd', 'doctor__user'
        )
        
        if since_date:
            queryset = queryset.filter(updated_at__gte=since_date)
        
        return list(queryset.all())
    
    records = await _get_records()
    total_records = len(records)
    
    logger.info(f"Found {total_records} clinical records to load")
    
    if total_records == 0:
        return 0
    
    # Process in batches
    loaded_count = 0
    
    for i in range(0, total_records, batch_size):
        batch = records[i:i + batch_size]
        
        try:
            # Prepare batch data
            documents = []
            embeddings = []
            ids = []
            metadatas = []
            
            for record in batch:
                # Create document text
                document_text = f"""
Lý do khám: {record.chief_complaint}
Bệnh sử: {record.history_of_present_illness}
Khám lâm sàng: {record.physical_exam}
Chẩn đoán: {record.final_diagnosis}
                """.strip()
                
                # Generate embedding
                embedding = await embed_clinical_note(
                    chief_complaint=record.chief_complaint,
                    history_of_present_illness=record.history_of_present_illness,
                    physical_exam=record.physical_exam,
                    embedding_service=embedding_service
                )
                
                # Prepare metadata
                metadata = {
                    'patient_id': str(record.visit.patient_id),
                    'visit_code': record.visit.visit_code,
                    'chief_complaint': record.chief_complaint[:200],  # Truncate for storage
                    'diagnosis': record.final_diagnosis[:200],
                    'main_icd_code': record.main_icd.code if record.main_icd else None,
                    'created_at': record.created_at.isoformat(),
                    'doctor': record.doctor.user.get_full_name() if record.doctor else None
                }
                
                documents.append(document_text)
                embeddings.append(embedding)
                ids.append(str(record.id))
                metadatas.append(metadata)
            
            # Add to vector database
            await vector_service.add_documents(
                collection_name='clinical_records',
                documents=documents,
                embeddings=embeddings,
                ids=ids,
                metadatas=metadatas
            )
            
            loaded_count += len(batch)
            logger.info(f"Loaded batch {i//batch_size + 1}: {loaded_count}/{total_records} records")
            
        except Exception as e:
            logger.error(f"Error loading batch {i//batch_size + 1}: {e}")
            # Continue with next batch
    
    logger.info(f"Completed loading {loaded_count} clinical records")
    return loaded_count


async def load_icd10_codes_to_vector_db(
    batch_size: int = 200,
    vector_service: Optional[VectorService] = None,
    embedding_service: Optional[EmbeddingService] = None
) -> int:
    """
    Load ICD-10 codes into vector database for semantic search.
    
    Args:
        batch_size: Number of codes to process per batch
        vector_service: VectorService instance (creates new if None)
        embedding_service: EmbeddingService instance (creates new if None)
        
    Returns:
        Number of codes loaded
    """
    from apps.core_services.core.models import ICD10Code
    
    logger.info(f"Starting ICD-10 codes loading (batch_size={batch_size})")
    
    # Initialize services
    if vector_service is None:
        vector_service = VectorService()
    if embedding_service is None:
        embedding_service = EmbeddingService()
    
    # Get all ICD-10 codes
    @sync_to_async
    def _get_codes():
        return list(ICD10Code.objects.select_related(
            'subcategory__category'
        ).all())
    
    codes = await _get_codes()
    total_codes = len(codes)
    
    logger.info(f"Found {total_codes} ICD-10 codes to load")
    
    if total_codes == 0:
        return 0
    
    # Process in batches
    loaded_count = 0
    
    for i in range(0, total_codes, batch_size):
        batch = codes[i:i + batch_size]
        
        try:
            # Prepare batch data
            documents = []
            embeddings = []
            ids = []
            metadatas = []
            
            for code in batch:
                # Create document text
                document_text = f"{code.code} - {code.name}"
                if code.description:
                    document_text += f"\n{code.description}"
                
                # Generate embedding
                embedding = await embed_icd10_code(
                    code=code.code,
                    name=code.name,
                    description=code.description,
                    embedding_service=embedding_service
                )
                
                # Prepare metadata
                metadata = {
                    'code': code.code,
                    'name': code.name,
                    'description': code.description,
                    'category': code.subcategory.category.name if code.subcategory else None,
                    'category_code': code.subcategory.category.code if code.subcategory else None,
                    'subcategory': code.subcategory.name if code.subcategory else None,
                }
                
                documents.append(document_text)
                embeddings.append(embedding)
                ids.append(str(code.id))
                metadatas.append(metadata)
            
            # Add to vector database
            await vector_service.add_documents(
                collection_name='icd10_codes',
                documents=documents,
                embeddings=embeddings,
                ids=ids,
                metadatas=metadatas
            )
            
            loaded_count += len(batch)
            logger.info(f"Loaded batch {i//batch_size + 1}: {loaded_count}/{total_codes} codes")
            
        except Exception as e:
            logger.error(f"Error loading batch {i//batch_size + 1}: {e}")
            # Continue with next batch
    
    logger.info(f"Completed loading {loaded_count} ICD-10 codes")
    return loaded_count


async def update_clinical_record_in_vector_db(
    record_id: str,
    vector_service: Optional[VectorService] = None,
    embedding_service: Optional[EmbeddingService] = None
) -> bool:
    """
    Update a single clinical record in vector database.
    
    Args:
        record_id: Clinical record UUID
        vector_service: VectorService instance (creates new if None)
        embedding_service: EmbeddingService instance (creates new if None)
        
    Returns:
        True if successful
    """
    from apps.medical_services.emr.models import ClinicalRecord
    
    # Initialize services
    if vector_service is None:
        vector_service = VectorService()
    if embedding_service is None:
        embedding_service = EmbeddingService()
    
    # Get record
    @sync_to_async
    def _get_record():
        try:
            return ClinicalRecord.objects.select_related(
                'visit__patient', 'main_icd', 'doctor__user'
            ).get(id=record_id)
        except ClinicalRecord.DoesNotExist:
            return None
    
    record = await _get_record()
    
    if not record:
        logger.warning(f"Clinical record not found: {record_id}")
        return False
    
    try:
        # Create document text
        document_text = f"""
Lý do khám: {record.chief_complaint}
Bệnh sử: {record.history_of_present_illness}
Khám lâm sàng: {record.physical_exam}
Chẩn đoán: {record.final_diagnosis}
        """.strip()
        
        # Generate embedding
        embedding = await embed_clinical_note(
            chief_complaint=record.chief_complaint,
            history_of_present_illness=record.history_of_present_illness,
            physical_exam=record.physical_exam,
            embedding_service=embedding_service
        )
        
        # Prepare metadata
        metadata = {
            'patient_id': str(record.visit.patient_id),
            'visit_code': record.visit.visit_code,
            'chief_complaint': record.chief_complaint[:200],
            'diagnosis': record.final_diagnosis[:200],
            'main_icd_code': record.main_icd.code if record.main_icd else None,
            'created_at': record.created_at.isoformat(),
            'doctor': record.doctor.user.get_full_name() if record.doctor else None
        }
        
        # Update in vector database
        await vector_service.update_documents(
            collection_name='clinical_records',
            documents=[document_text],
            embeddings=[embedding],
            ids=[str(record.id)],
            metadatas=[metadata]
        )
        
        logger.info(f"Updated clinical record in vector DB: {record_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating clinical record in vector DB: {e}")
        return False


async def load_departments_to_vector_db(
    vector_service: Optional[VectorService] = None,
    embedding_service: Optional[EmbeddingService] = None
) -> int:
    """
    Load departments vào vector database cho semantic search.
    
    Mỗi department được embed với: tên + mô tả + chuyên khoa + triệu chứng.
    AI triage agent dùng semantic search để tìm khoa phù hợp theo triệu chứng.
    
    Args:
        vector_service: VectorService instance (creates new if None)
        embedding_service: EmbeddingService instance (creates new if None)
        
    Returns:
        Number of departments loaded
    """
    from apps.core_services.departments.models import Department
    
    logger.info("Starting departments loading to vector DB")
    
    # Initialize services
    if vector_service is None:
        vector_service = VectorService()
    if embedding_service is None:
        embedding_service = EmbeddingService()
    
    # Get active departments
    @sync_to_async
    def _get_departments():
        return list(Department.objects.filter(is_active=True))
    
    departments = await _get_departments()
    total = len(departments)
    
    logger.info(f"Found {total} active departments to load")
    
    if total == 0:
        return 0
    
    loaded_count = 0
    
    for dept in departments:
        try:
            # Create document text (rich context for search)
            document_text = (
                f"Khoa phòng: {dept.name} (Mã: {dept.code})\n"
                f"Chức năng: {dept.description}\n"
                f"Chuyên khoa: {dept.specialties}\n"
                f"Triệu chứng điển hình: {dept.typical_symptoms}"
            )
            
            # Generate embedding
            embedding = await embed_department(
                name=dept.name,
                code=dept.code,
                description=dept.description,
                specialties=dept.specialties,
                typical_symptoms=dept.typical_symptoms,
                embedding_service=embedding_service
            )
            
            # Metadata
            metadata = {
                'code': dept.code,
                'name': dept.name,
                'specialties': dept.specialties[:200],
                'typical_symptoms': dept.typical_symptoms[:300],
            }
            
            # Add to vector database
            await vector_service.add_documents(
                collection_name='departments',
                documents=[document_text],
                embeddings=[embedding],
                ids=[str(dept.id)],
                metadatas=[metadata]
            )
            
            loaded_count += 1
            logger.info(f"Loaded department: {dept.code} - {dept.name}")
            
        except Exception as e:
            logger.error(f"Error loading department {dept.code}: {e}")
    
    logger.info(f"Completed loading {loaded_count} departments")
    return loaded_count
