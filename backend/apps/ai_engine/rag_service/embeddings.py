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
    
    def __init__(self, provider: str = 'sentence-transformers', model_name: Optional[str] = None):
        """
        Initialize embedding service.
        
        Args:
            provider: Embedding provider ('google', 'sentence-transformers')
            model_name: Specific model name (provider-dependent)
        """
        self.provider = provider
        self.model_name = model_name
        self._embedding_model = None
        self._embedding_cache: Dict[str, List[float]] = {}
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the embedding model based on provider."""
        try:
            if self.provider == 'google':
                self._init_google_embeddings()
            elif self.provider == 'sentence-transformers':
                self._init_sentence_transformers()
            else:
                raise ValueError(f"Unsupported embedding provider: {self.provider}")
                
            logger.info(f"Initialized {self.provider} embedding model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            # Fallback to sentence-transformers
            if self.provider != 'sentence-transformers':
                logger.warning("Falling back to sentence-transformers")
                self.provider = 'sentence-transformers'
                self._init_sentence_transformers()
    
    def _init_google_embeddings(self):
        """Initialize Google GenAI embeddings."""
        try:
            import google.genai as genai
            from django.conf import settings
            
            api_key = getattr(settings, 'GOOGLE_API_KEY', None)
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in settings")
            
            # Configure the client
            client = genai.Client(api_key=api_key)
            self.model_name = self.model_name or 'gemini-embedding-001'
            self._embedding_model = client
            
        except ImportError:
            raise ImportError("google-genai not installed. Run: pip install google-genai")
    

    
    def _init_sentence_transformers(self):
        """Initialize local Sentence Transformers."""
        try:
            from sentence_transformers import SentenceTransformer
            
            self.model_name = self.model_name or 'all-MiniLM-L6-v2'
            self._embedding_model = SentenceTransformer(self.model_name)
            
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
    
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
            if self.provider == 'google':
                embedding = await self._embed_google(text)
            else:  # sentence-transformers
                embedding = await self._embed_sentence_transformer(text)
            
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
            result = self._embedding_model.models.embed_content(
                model=self.model_name,
                content=text
            )
            return result.embeddings[0].values
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_embed)
    

    
    async def _embed_sentence_transformer(self, text: str) -> List[float]:
        """Generate embedding using Sentence Transformers."""
        import asyncio
        
        def _sync_embed():
            embedding = self._embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        
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
        if len(texts) <= 10:
            tasks = [self.embed_text(text, use_cache=use_cache) for text in texts]
            return await asyncio.gather(*tasks)
        
        # For large batches, use batch processing if available
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text, use_cache=use_cache)
            embeddings.append(embedding)
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings from this model."""
        dimension_map = {
            'all-MiniLM-L6-v2': 384,
            'all-mpnet-base-v2': 768,
            'gemini-embedding-001': 768,
            'models/embedding-001': 768,  # Legacy
        }
        
        return dimension_map.get(self.model_name, 768)  # Default to 768


async def embed_clinical_note(
    chief_complaint: str,
    history_of_present_illness: str,
    physical_exam: str,
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
    combined_text = f"""
    Lý do khám: {chief_complaint}
    
    Bệnh sử: {history_of_present_illness}
    
    Khám lâm sàng: {physical_exam}
    """.strip()
    
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
