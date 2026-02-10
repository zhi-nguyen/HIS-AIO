"""
Search Helper for AI Agents

Cung cấp interface đơn giản để AI agents lấy RAG context trước khi prompt LLM.
"""

import logging
from typing import List, Dict, Any, Optional

from .vector_service import VectorService
from .embeddings import EmbeddingService, get_embedding
from .context_retrieval import retrieve_patient_context, format_context_for_llm

logger = logging.getLogger(__name__)


async def get_rag_context(
    query: str,
    collection: str = 'clinical_records',
    top_k: int = 5,
    where: Optional[Dict[str, Any]] = None,
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Lấy RAG context cho AI agent prompts.
    
    Sử dụng semantic search để tìm các documents liên quan đến query.
    
    Args:
        query: Câu hỏi hoặc context cần tìm kiếm
        collection: Tên collection ('clinical_records', 'icd10_codes', 'drugs', etc.)
        top_k: Số kết quả tối đa
        where: Filter metadata (e.g., {'patient_id': 'uuid'})
        similarity_threshold: Ngưỡng similarity tối thiểu (0-1)
        
    Returns:
        List[Dict]: Danh sách documents với metadata và similarity scores
        
    Example:
        >>> results = await get_rag_context(
        ...     query="Bệnh nhân đau đầu, sốt cao",
        ...     collection="clinical_records",
        ...     top_k=3
        ... )
        >>> for r in results:
        ...     print(f"Score: {r['similarity']:.2f} - {r['document'][:100]}")
    """
    try:
        embedding_service = EmbeddingService()
        vector_service = VectorService()
        
        # Generate query embedding
        query_embedding = await embedding_service.embed_text(query)
        
        if not query_embedding:
            logger.warning("Failed to generate query embedding")
            return []
        
        # Semantic search
        results = await vector_service.semantic_search(
            collection_name=collection,
            query_embedding=query_embedding,
            top_k=top_k,
            where=where,
            similarity_threshold=similarity_threshold
        )
        
        logger.info(f"RAG search returned {len(results)} results for query: {query[:50]}...")
        return results
        
    except Exception as e:
        logger.error(f"Error in get_rag_context: {e}")
        return []


async def get_patient_rag_context(
    patient_id: str,
    query: Optional[str] = None,
    top_k: int = 5
) -> str:
    """
    Lấy patient context đã format sẵn cho LLM prompt.
    
    Kết hợp patient demographics, clinical history, và prescriptions.
    
    Args:
        patient_id: UUID của bệnh nhân
        query: Query để semantic search (optional, nếu None sẽ lấy records mới nhất)
        top_k: Số lượng clinical records tối đa
        
    Returns:
        str: Context đã format sẵn cho LLM
        
    Example:
        >>> context = await get_patient_rag_context(
        ...     patient_id="123e4567-e89b-12d3-a456-426614174000",
        ...     query="tiền sử tim mạch"
        ... )
        >>> print(context)
        THÔNG TIN BỆNH NHÂN:
        - Mã bệnh nhân: BN-001
        ...
    """
    try:
        # Use existing context retrieval
        context_dict = await retrieve_patient_context(
            patient_id=patient_id,
            query=query,
            top_k_records=top_k
        )
        
        # Format for LLM
        formatted = format_context_for_llm(context_dict, include_pii=True)
        return formatted
        
    except Exception as e:
        logger.error(f"Error getting patient RAG context: {e}")
        return f"Không thể lấy thông tin bệnh nhân: {str(e)}"


def get_rag_context_sync(
    query: str,
    collection: str = 'clinical_records',
    top_k: int = 5,
    where: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for get_rag_context.
    
    Tiện dụng cho code sync không cần async/await.
    
    Args:
        query: Câu hỏi hoặc context cần tìm kiếm
        collection: Tên collection
        top_k: Số kết quả tối đa
        where: Filter metadata
        
    Returns:
        List[Dict]: Danh sách documents
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    get_rag_context(query, collection, top_k, where)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                get_rag_context(query, collection, top_k, where)
            )
    except RuntimeError:
        return asyncio.run(get_rag_context(query, collection, top_k, where))
