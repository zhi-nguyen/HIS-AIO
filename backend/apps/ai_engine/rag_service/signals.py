"""
Django Signals for RAG Service Auto-Indexing

Tự động cập nhật VectorDocument khi ClinicalRecord thay đổi.
"""

import logging
import threading
import asyncio
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _run_async_indexing(record_id: str):
    """
    Chạy async indexing trong background thread.
    
    Args:
        record_id: ID của ClinicalRecord cần index
    """
    from .data_loader import update_clinical_record_in_vector_db
    
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                update_clinical_record_in_vector_db(record_id)
            )
            if result:
                logger.info(f"Successfully indexed ClinicalRecord {record_id} to vector DB")
            else:
                logger.warning(f"Failed to index ClinicalRecord {record_id}")
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error indexing ClinicalRecord {record_id}: {e}")


@receiver(post_save, sender='emr.ClinicalRecord')
def index_clinical_record_on_save(sender, instance, created, **kwargs):
    """
    Signal handler: Tự động index ClinicalRecord vào VectorDocument khi save.
    
    Chạy trong background thread để không block request.
    
    Args:
        sender: Model class (ClinicalRecord)
        instance: ClinicalRecord instance được save
        created: True nếu là record mới, False nếu update
    """
    record_id = str(instance.id)
    action = "created" if created else "updated"
    
    logger.info(f"ClinicalRecord {action}: {record_id}, queueing for RAG indexing...")
    
    # Run indexing in background thread to avoid blocking
    thread = threading.Thread(
        target=_run_async_indexing,
        args=(record_id,),
        daemon=True
    )
    thread.start()


@receiver(post_delete, sender='emr.ClinicalRecord')
def remove_clinical_record_on_delete(sender, instance, **kwargs):
    """
    Signal handler: Xóa ClinicalRecord khỏi VectorDocument khi delete.
    
    Args:
        sender: Model class (ClinicalRecord)
        instance: ClinicalRecord instance bị xóa
    """
    from .vector_service import VectorService
    
    record_id = str(instance.id)
    logger.info(f"ClinicalRecord deleted: {record_id}, removing from vector DB...")
    
    def _run_delete():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                service = VectorService()
                loop.run_until_complete(
                    service.delete_documents(
                        collection_name='clinical_records',
                        ids=[record_id]
                    )
                )
                logger.info(f"Removed ClinicalRecord {record_id} from vector DB")
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error removing ClinicalRecord {record_id} from vector DB: {e}")
    
    thread = threading.Thread(target=_run_delete, daemon=True)
    thread.start()
