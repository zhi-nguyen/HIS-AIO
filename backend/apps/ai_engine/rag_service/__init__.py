"""
RAG Service Package for Healthcare Information System

This package provides Retrieval-Augmented Generation capabilities including:
- Vector storage and semantic search
- Clinical context retrieval
- Hybrid search for ICD-10 codes and symptoms
- PII-safe logging and data handling
"""

from .vector_service import VectorService
from .context_retrieval import retrieve_patient_context, format_context_for_llm
from .hybrid_search import HybridSearchService
from .embeddings import EmbeddingService, get_embedding

__all__ = [
    'VectorService',
    'retrieve_patient_context',
    'format_context_for_llm',
    'HybridSearchService',
    'EmbeddingService',
    'get_embedding',
]

