"""
Vector Service for Healthcare RAG using PgVector

Provides vector storage, semantic search, and collection management
for clinical records and ICD-10 codes using PostgreSQL with PgVector extension.
"""

import logging
from typing import List, Dict, Any, Optional
from asgiref.sync import sync_to_async
from django.db.models import Q, F
from pgvector.django import CosineDistance

logger = logging.getLogger(__name__)


class VectorService:
    """
    Service for managing vector storage and semantic search using PgVector.
    
    Handles document embedding, storage, and retrieval for RAG operations
    using PostgreSQL with the pgvector extension.
    """
    
    def __init__(self):
        """
        Initialize PgVector service.
        
        Uses Django's database connection, no additional initialization needed.
        """
        logger.info("Initialized PgVector service with PostgreSQL")
    
    async def get_or_create_collection(
        self,
        collection_name: str,
        embedding_dimension: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get or verify collection exists.
        
        For PgVector, collections are managed via the collection field in VectorDocument.
        This method validates the collection name.
        
        Args:
            collection_name: Name of the collection ('clinical_records' or 'icd10_codes')
            embedding_dimension: Not used in PgVector (dimension is fixed in model)
            metadata: Not used in PgVector
            
        Returns:
            Collection name if valid
        """
        from .models import VectorDocument
        
        valid_collections = [choice[0] for choice in VectorDocument.CollectionType.choices]
        
        if collection_name not in valid_collections:
            raise ValueError(
                f"Invalid collection name '{collection_name}'. "
                f"Must be one of: {valid_collections}"
            )
        
        logger.debug(f"Using collection: {collection_name}")
        return collection_name
    
    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        ids: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Add documents to a collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of document texts
            embeddings: List of embedding vectors
            ids: List of unique document IDs
            metadatas: Optional list of metadata dicts
            
        Returns:
            True if successful
        """
        from .models import VectorDocument
        
        if len(documents) != len(embeddings) != len(ids):
            raise ValueError("documents, embeddings, and ids must have same length")
        
        @sync_to_async
        def _add_documents():
            created_count = 0
            
            for i in range(len(documents)):
                metadata = metadatas[i] if metadatas else {}
                
                # Create or update document
                VectorDocument.objects.update_or_create(
                    collection=collection_name,
                    document_id=ids[i],
                    defaults={
                        'document_text': documents[i],
                        'embedding': embeddings[i],
                        'metadata': metadata
                    }
                )
                created_count += 1
            
            logger.info(f"Added {created_count} documents to {collection_name}")
            return True
        
        return await _add_documents()
    
    async def update_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        ids: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Update existing documents in collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of document texts
            embeddings: List of embedding vectors
            ids: List of document IDs to update
            metadatas: Optional list of metadata dicts
            
        Returns:
            True if successful
        """
        # For PgVector, add_documents handles both insert and update via update_or_create
        return await self.add_documents(collection_name, documents, embeddings, ids, metadatas)
    
    async def delete_documents(
        self,
        collection_name: str,
        ids: List[str]
    ) -> bool:
        """
        Delete documents from collection.
        
        Args:
            collection_name: Name of the collection
            ids: List of document IDs to delete
            
        Returns:
            True if successful
        """
        from .models import VectorDocument
        
        @sync_to_async
        def _delete_documents():
            deleted_count, _ = VectorDocument.objects.filter(
                collection=collection_name,
                document_id__in=ids
            ).delete()
            
            logger.info(f"Deleted {deleted_count} documents from {collection_name}")
            return True
        
        return await _delete_documents()
    
    async def semantic_search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search in a collection using cosine similarity.
        
        Args:
            collection_name: Name of the collection to search
            query_embedding: Query embedding vector
            top_k: Number of results to return
            where: Optional metadata filter (e.g., {'patient_id': 'uuid'})
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of search results with documents, metadata, and scores
        """
        from .models import VectorDocument
        
        @sync_to_async
        def _search():
            # Start with collection filter
            queryset = VectorDocument.objects.filter(collection=collection_name)
            
            # Apply metadata filters if provided
            if where:
                for key, value in where.items():
                    # Use JSONB contains operator
                    queryset = queryset.filter(**{f'metadata__{key}': value})
            
            # Perform vector similarity search using cosine distance
            queryset = queryset.annotate(
                distance=CosineDistance('embedding', query_embedding)
            ).order_by('distance')[:top_k]
            
            # Parse and format results
            results = []
            for doc in queryset:
                # Convert distance to similarity (1 - distance for cosine)
                similarity = 1 - doc.distance
                
                # Apply similarity threshold if specified
                if similarity_threshold and similarity < similarity_threshold:
                    continue
                
                results.append({
                    'id': doc.document_id,
                    'document': doc.document_text,
                    'metadata': doc.metadata,
                    'similarity': similarity,
                    'distance': doc.distance
                })
            
            logger.debug(f"Semantic search returned {len(results)} results")
            return results
        
        return await _search()
    
    async def get_collection_count(self, collection_name: str) -> int:
        """
        Get number of documents in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Number of documents
        """
        from .models import VectorDocument
        
        @sync_to_async
        def _count():
            return VectorDocument.objects.filter(collection=collection_name).count()
        
        return await _count()
    
    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete all documents in a collection.
        
        Args:
            collection_name: Name of the collection to clear
            
        Returns:
            True if successful
        """
        from .models import VectorDocument
        
        @sync_to_async
        def _delete_collection():
            deleted_count, _ = VectorDocument.objects.filter(
                collection=collection_name
            ).delete()
            
            logger.info(f"Deleted collection '{collection_name}' ({deleted_count} documents)")
            return True
        
        return await _delete_collection()
