"""
Hybrid Search Service for ICD-10 Codes and Clinical Symptoms

Combines keyword-based search with semantic search for optimal retrieval:
- Keyword search: Exact/prefix matching for ICD-10 codes
- Semantic search: Similarity-based matching for symptoms and descriptions
- Hybrid ranking: Reciprocal Rank Fusion (RRF) for result combination
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from asgiref.sync import sync_to_async

from .vector_service import VectorService
from .embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class HybridSearchService:
    """
    Service for hybrid search combining keyword and semantic approaches.
    
    Particularly useful for medical terminology where exact codes and
    natural language descriptions both matter.
    """
    
    def __init__(
        self,
        vector_service: Optional[VectorService] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Initialize hybrid search service.
        
        Args:
            vector_service: VectorService instance (creates new if None)
            embedding_service: EmbeddingService instance (creates new if None)
        """
        self.vector_service = vector_service or VectorService()
        self.embedding_service = embedding_service or EmbeddingService()
    
    async def search_icd10_by_code(
        self,
        code_query: str,
        exact_match: bool = False,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search ICD-10 codes using keyword matching.
        
        Args:
            code_query: ICD-10 code query (e.g., "J00", "I10")
            exact_match: If True, only exact matches; if False, prefix matching
            top_k: Maximum number of results
            
        Returns:
            List of matching ICD-10 codes with metadata
        """
        from apps.core_services.core.models import ICD10Code
        
        @sync_to_async
        def _keyword_search():
            try:
                # Normalize query
                code_query_upper = code_query.upper().strip()
                
                # Build query
                if exact_match:
                    queryset = ICD10Code.objects.filter(code__iexact=code_query_upper)
                else:
                    # Prefix matching (e.g., "J0" matches "J00", "J01", etc.)
                    queryset = ICD10Code.objects.filter(code__istartswith=code_query_upper)
                
                # Get results
                results = queryset.select_related('subcategory__category')[:top_k]
                
                # Format results
                formatted_results = []
                for i, icd_code in enumerate(results):
                    formatted_results.append({
                        'id': str(icd_code.id),
                        'code': icd_code.code,
                        'name': icd_code.name,
                        'description': icd_code.description,
                        'category': icd_code.subcategory.category.name if icd_code.subcategory else None,
                        'category_code': icd_code.subcategory.category.code if icd_code.subcategory else None,
                        'rank': i + 1,
                        'score': 1.0 / (i + 1),  # Simple ranking score
                        'search_type': 'keyword'
                    })
                
                logger.info(f"Keyword search for '{code_query}' returned {len(formatted_results)} results")
                return formatted_results
                
            except Exception as e:
                logger.error(f"Error in keyword search: {e}")
                return []
        
        return await _keyword_search()
    
    async def search_icd10_by_symptoms(
        self,
        symptom_query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search ICD-10 codes using semantic similarity to symptoms.
        
        Args:
            symptom_query: Natural language symptom description
            top_k: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of relevant ICD-10 codes with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.embed_text(symptom_query)
            
            # Semantic search in ICD-10 collection
            results = await self.vector_service.semantic_search(
                collection_name='icd10_codes',
                query_embedding=query_embedding,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            # Format results
            formatted_results = []
            for i, result in enumerate(results):
                metadata = result.get('metadata', {})
                formatted_results.append({
                    'id': result['id'],
                    'code': metadata.get('code'),
                    'name': metadata.get('name'),
                    'description': metadata.get('description'),
                    'category': metadata.get('category'),
                    'category_code': metadata.get('category_code'),
                    'rank': i + 1,
                    'score': result.get('similarity', 0),
                    'search_type': 'semantic'
                })
            
            logger.info(f"Semantic search for '{symptom_query}' returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6,
        auto_detect_code: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining keyword and semantic approaches.
        
        Uses Reciprocal Rank Fusion (RRF) to combine results from both methods.
        
        Args:
            query: Search query (code or symptoms)
            top_k: Maximum number of results
            keyword_weight: Weight for keyword search results (0-1)
            semantic_weight: Weight for semantic search results (0-1)
            auto_detect_code: If True, auto-detect if query is a code
            
        Returns:
            Combined and ranked list of ICD-10 codes
        """
        # Auto-detect if query looks like an ICD-10 code
        is_code_query = False
        if auto_detect_code:
            # Simple heuristic: starts with letter, contains numbers, short length
            query_stripped = query.strip()
            if len(query_stripped) <= 6 and query_stripped[0].isalpha():
                is_code_query = True
        
        # Perform both searches
        keyword_results = []
        semantic_results = []
        
        if is_code_query:
            # Prioritize keyword search for code queries
            keyword_results = await self.search_icd10_by_code(query, exact_match=False, top_k=top_k)
            # Still do semantic search for completeness
            semantic_results = await self.search_icd10_by_symptoms(query, top_k=top_k)
        else:
            # Prioritize semantic search for symptom queries
            semantic_results = await self.search_icd10_by_symptoms(query, top_k=top_k)
            # Try keyword search in case query contains a code
            if any(char.isdigit() for char in query):
                keyword_results = await self.search_icd10_by_code(query, exact_match=False, top_k=top_k)
        
        # Combine using Reciprocal Rank Fusion
        combined_results = self._reciprocal_rank_fusion(
            keyword_results=keyword_results,
            semantic_results=semantic_results,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight
        )
        
        # Return top k
        return combined_results[:top_k]
    
    def _reciprocal_rank_fusion(
        self,
        keyword_results: List[Dict[str, Any]],
        semantic_results: List[Dict[str, Any]],
        keyword_weight: float = 0.5,
        semantic_weight: float = 0.5,
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine results using Reciprocal Rank Fusion (RRF).
        
        RRF formula: score(d) = Σ (1 / (k + rank(d)))
        
        Args:
            keyword_results: Results from keyword search
            semantic_results: Results from semantic search
            keyword_weight: Weight for keyword results
            semantic_weight: Weight for semantic results
            k: RRF constant (typically 60)
            
        Returns:
            Combined and sorted results
        """
        # Build score dictionary
        scores: Dict[str, Dict[str, Any]] = {}
        
        # Process keyword results
        for result in keyword_results:
            result_id = result['code']  # Use code as identifier
            rank = result.get('rank', 1)
            rrf_score = keyword_weight / (k + rank)
            
            if result_id not in scores:
                scores[result_id] = {
                    **result,
                    'rrf_score': 0,
                    'keyword_rank': None,
                    'semantic_rank': None
                }
            
            scores[result_id]['rrf_score'] += rrf_score
            scores[result_id]['keyword_rank'] = rank
        
        # Process semantic results
        for result in semantic_results:
            result_id = result['code']
            rank = result.get('rank', 1)
            rrf_score = semantic_weight / (k + rank)
            
            if result_id not in scores:
                scores[result_id] = {
                    **result,
                    'rrf_score': 0,
                    'keyword_rank': None,
                    'semantic_rank': None
                }
            
            scores[result_id]['rrf_score'] += rrf_score
            scores[result_id]['semantic_rank'] = rank
        
        # Sort by RRF score
        combined = sorted(
            scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )
        
        # Add final rank
        for i, result in enumerate(combined, 1):
            result['final_rank'] = i
            result['search_type'] = 'hybrid'
        
        logger.info(f"Hybrid search combined {len(keyword_results)} keyword + {len(semantic_results)} semantic = {len(combined)} total results")
        
        return combined
