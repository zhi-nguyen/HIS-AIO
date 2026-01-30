"""
Embedding Service for Clinical Text

Provides embedding generation with support for multiple backends:
- Google GenAI Embeddings (gemini-embedding-001)
- Local Sentence Transformers (default)

Uses caching to avoid re-embedding identical text.
"""

import logging
from typing import List, Optional, Dict, Any
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings from clinical text.
    
    Supports multiple embedding backends and includes caching.
    """
    
    
    def __init__(self, provider: str = 'google', model_name: Optional[str] = None):
        """
        Initialize embedding service.
        
        Args:
            provider: Embedding provider ('google') - default and only supported
            model_name: Specific model name (provider-dependent)
        """
        self.provider = 'google'  # Enforce google
        self.model_name = model_name
        self._embedding_model = None
        self._embedding_cache: Dict[str, List[float]] = {}
        self._dimension = 768 # Default
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the embedding model based on provider."""
        try:
            self._init_google_embeddings()
            logger.info(f"Initialized Google embedding model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise RuntimeError("Failed to initialize Google GenAI embeddings. Ensure GOOGLE_API_KEY is set.")
    
    def _init_google_embeddings(self):
        """Initialize Google GenAI embeddings."""
        try:
            import google.genai as genai
            from django.conf import settings
            from apps.ai_engine.agents.models import VectorStore
            
            # 1. Try to load from Database (VectorStore)
            vector_config = VectorStore.get_active_config()
            
            if vector_config:
                self.model_name = vector_config.embedding_model or self.model_name
                self._dimension = vector_config.dimensions
                logger.info(f"Loaded embedding config from DB: {self.model_name} ({self._dimension}d)")
            
            # 2. Fallback to settings or default
            if not self.model_name:
                self.model_name = getattr(settings, 'RAG_EMBEDDING_MODEL', 'models/text-embedding-004')
                
            api_key = getattr(settings, 'GOOGLE_API_KEY', None)
            if not api_key:
                # Try getting from os environment if not in settings
                import os
                api_key = os.environ.get('GOOGLE_API_KEY')
                
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in settings or environment")
            
            # Configure the client
            client = genai.Client(api_key=api_key)
            # Use text-embedding-004 which supports output_dimensionality
            self.model_name = self.model_name or 'models/text-embedding-004'
            self._embedding_model = client
            
        except ImportError:
            raise ImportError("google-genai not installed. Run: pip install google-genai")
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def embed_text(self, text: str, use_cache: bool = True) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            use_cache: Whether to use cached embeddings
            
        Returns:
            Embedding vector as list of floats
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return []
        
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self._embedding_cache:
                logger.debug(f"Cache hit for text: {text[:50]}...")
                return self._embedding_cache[cache_key]
        
        # Generate embedding
        try:
            embedding = await self._embed_google(text)
            
            # Cache result
            if use_cache:
                cache_key = self._get_cache_key(text)
                self._embedding_cache[cache_key] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def _embed_google(self, text: str) -> List[float]:
        """Generate embedding using Google GenAI."""
        import asyncio
        
        def _sync_embed():
            # Use configured dimension
            result = self._embedding_model.models.embed_content(
                model=self.model_name,
                contents=text,
                config={'output_dimensionality': self._dimension}
            )
            return result.embeddings[0].values
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_embed)

    async def embed_batch(self, texts: List[str], use_cache: bool = True) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            use_cache: Whether to use cached embeddings
            
        Returns:
            List of embedding vectors
        """
        import asyncio
        
        # For small batches, use concurrent individual calls
        # Note: Google GenAI might have batch support, but for now we stick to implementation
        # that definitely works with current client pattern or use simple loop/gather
        if len(texts) <= 10:
            tasks = [self.embed_text(text, use_cache=use_cache) for text in texts]
            return await asyncio.gather(*tasks)
        
        # For large batches, process in chunks to respect rate limits if needed
        # For now, just linear async calls
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text, use_cache=use_cache)
            embeddings.append(embedding)
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings from this model."""
        return self._dimension


async def embed_clinical_note(
    chief_complaint: str,
    history_of_present_illness: str,
    physical_exam: str,
    final_diagnosis: Optional[str] = None,
    treatment_plan: Optional[str] = None,
    embedding_service: Optional[EmbeddingService] = None
) -> List[float]:
    """
    Generate embedding for a clinical note.
    
    Combines chief complaint, history, and physical exam into a single embedding.
    
    Args:
        chief_complaint: Patient's chief complaint
        history_of_present_illness: Patient's medical history
        physical_exam: Physical examination findings
        embedding_service: EmbeddingService instance (creates new if None)
        
    Returns:
        Embedding vector for the clinical note
    """
    if embedding_service is None:
        embedding_service = EmbeddingService()
    
    # Combine clinical text
    parts = [
        f"Lý do khám/Triệu chứng chính: {chief_complaint}",
        f"Bệnh sử: {history_of_present_illness}",
        f"Khám lâm sàng: {physical_exam}"
    ]
    
    if final_diagnosis:
        parts.append(f"Chẩn đoán: {final_diagnosis}")
    
    if treatment_plan:
        parts.append(f"Hướng dẫn điều trị: {treatment_plan}")
        
    combined_text = "\n\n".join(parts)
    
    return await embedding_service.embed_text(combined_text)


async def embed_drug_info(
    name: str,
    usage: str,
    contraindications: Optional[str] = None,
    side_effects: Optional[str] = None,
    embedding_service: Optional[EmbeddingService] = None
) -> List[float]:
    """
    Generate embedding for drug information.
    
    Args:
        name: Drug name
        usage: Usage instructions
        contraindications: Contraindications (optional)
        side_effects: Side effects (optional)
        embedding_service: EmbeddingService instance
        
    Returns:
        Embedding vector for the drug
    """
    if embedding_service is None:
        embedding_service = EmbeddingService()
        
    parts = [
        f"Thuốc: {name}",
        f"Chỉ định/Cách dùng: {usage}"
    ]
    
    if contraindications:
        parts.append(f"Chống chỉ định: {contraindications}")
        
    if side_effects:
        parts.append(f"Tác dụng phụ: {side_effects}")
        
    combined_text = "\n\n".join(parts)
    return await embedding_service.embed_text(combined_text)


async def embed_medical_protocol(
    title: str,
    content: str,
    category: Optional[str] = None,
    embedding_service: Optional[EmbeddingService] = None
) -> List[float]:
    """
    Generate embedding for a medical protocol.
    
    Args:
        title: Protocol title
        content: Protocol content
        category: Protocol category (optional)
        embedding_service: EmbeddingService instance
        
    Returns:
        Embedding vector
    """
    if embedding_service is None:
        embedding_service = EmbeddingService()
        
    parts = [f"Phác đồ: {title}"]
    
    if category:
        parts.append(f"Danh mục: {category}")
        
    parts.append(f"Nội dung: {content}")
    
    combined_text = "\n\n".join(parts)
    return await embedding_service.embed_text(combined_text)


async def embed_hospital_process(
    question: str,
    answer: str,
    category: Optional[str] = None,
    embedding_service: Optional[EmbeddingService] = None
) -> List[float]:
    """
    Generate embedding for hospital process Q&A.
    
    Args:
        question: Question about process
        answer: Answer/Guidance
        category: Process category (optional)
        embedding_service: EmbeddingService instance
        
    Returns:
        Embedding vector
    """
    if embedding_service is None:
        embedding_service = EmbeddingService()
        
    parts = []
    if category:
        parts.append(f"Chủ đề: {category}")
        
    parts.append(f"Câu hỏi: {question}")
    parts.append(f"Trả lời: {answer}")
    
    combined_text = "\n\n".join(parts)
    return await embedding_service.embed_text(combined_text)


async def embed_icd10_code(
    code: str,
    name: str,
    description: Optional[str] = None,
    embedding_service: Optional[EmbeddingService] = None
) -> List[float]:
    """
    Generate embedding for an ICD-10 code.
    
    Args:
        code: ICD-10 code
        name: Disease name
        description: Optional description
        embedding_service: EmbeddingService instance (creates new if None)
        
    Returns:
        Embedding vector for the ICD-10 code
    """
    if embedding_service is None:
        embedding_service = EmbeddingService()
    
    # Combine ICD-10 information
    combined_text = f"{code} - {name}"
    if description:
        combined_text += f"\n{description}"
    
    return await embedding_service.embed_text(combined_text)
