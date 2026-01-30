"""
Redis Caching for RAG Results

Provides Redis-based caching for:
- ICD-10 code lookups (high hit rate, 24h TTL)
- Drug interaction queries (1h TTL)
- Common symptom embeddings (6h TTL)
- RAG search results (configurable TTL)
"""

import json
import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar
from functools import wraps

from django.conf import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RAGCache:
    """
    Redis-based cache for RAG query results.
    
    Strategies:
    1. Cache ICD-10 code lookups (TTL: 24h, high hit rate)
    2. Cache drug interaction queries (TTL: 1h)
    3. Cache common symptom embeddings (TTL: 6h)
    4. Cache RAG search results by query hash (TTL: configurable)
    
    Example:
        cache = RAGCache()
        
        # Using get_or_compute
        result = cache.get_or_compute(
            "icd10:J06.9",
            lambda: lookup_icd10("J06.9"),
            ttl=86400  # 24h
        )
        
        # Using decorator
        @cache.cached("drug_interaction", ttl=3600)
        def check_drug_interaction(drug_a: str, drug_b: str) -> Dict:
            ...
    """
    
    # TTL presets (in seconds)
    TTL_ICD10 = 86400       # 24 hours
    TTL_DRUG_INTERACTION = 3600  # 1 hour
    TTL_SYMPTOM_EMBEDDING = 21600  # 6 hours
    TTL_RAG_SEARCH = 1800   # 30 minutes
    TTL_DEFAULT = 3600      # 1 hour
    
    def __init__(self):
        """Initialize Redis connection."""
        self._redis = None
        self._connected = False
        self._connection_attempted = False
    
    @property
    def redis(self):
        """Lazy Redis connection."""
        if not self._connection_attempted:
            self._connection_attempted = True
            try:
                import redis
                self._redis = redis.Redis(
                    host=getattr(settings, 'REDIS_HOST', 'localhost'),
                    port=getattr(settings, 'REDIS_PORT', 6379),
                    db=getattr(settings, 'REDIS_DB', 0),
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                # Test connection
                self._redis.ping()
                self._connected = True
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis not available, caching disabled: {e}")
                self._redis = None
                self._connected = False
        return self._redis
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self.redis is not None
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate cache key from prefix and arguments.
        
        Args:
            prefix: Key prefix (e.g., 'icd10', 'drug_interaction')
            *args: Positional arguments to hash
            **kwargs: Keyword arguments to hash
            
        Returns:
            Cache key string
        """
        # Create stable hash from arguments
        key_data = json.dumps(
            {"args": args, "kwargs": kwargs},
            sort_keys=True,
            ensure_ascii=False
        )
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"rag:{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.is_connected:
            return None
        
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds (default: TTL_DEFAULT)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False
        
        ttl = ttl or self.TTL_DEFAULT
        
        try:
            # ensure_ascii=False to preserve Vietnamese characters
            json_value = json.dumps(value, ensure_ascii=False)
            self.redis.setex(key, ttl, json_value)
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], T],
        ttl: int = None
    ) -> T:
        """
        Get from cache or compute and cache the result.
        
        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            ttl: Time-to-live in seconds
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache
        cached = self.get(key)
        if cached is not None:
            logger.debug(f"Cache hit: {key}")
            return cached
        
        # Compute value
        logger.debug(f"Cache miss: {key}")
        result = compute_fn()
        
        # Cache the result
        self.set(key, result, ttl)
        
        return result
    
    def cached(self, prefix: str, ttl: int = None):
        """
        Decorator for caching function results.
        
        Args:
            prefix: Key prefix for this function
            ttl: Time-to-live in seconds
            
        Returns:
            Decorator function
            
        Example:
            @cache.cached("icd10", ttl=86400)
            def lookup_icd10(code: str) -> Dict:
                ...
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                key = self._make_key(prefix, *args, **kwargs)
                return self.get_or_compute(
                    key,
                    lambda: func(*args, **kwargs),
                    ttl
                )
            return wrapper
        return decorator
    
    def cache_icd10(self, code: str, data: Dict) -> bool:
        """
        Cache ICD-10 lookup result.
        
        Args:
            code: ICD-10 code
            data: Lookup result data
            
        Returns:
            True if cached successfully
        """
        key = f"rag:icd10:{code.upper()}"
        return self.set(key, data, self.TTL_ICD10)
    
    def get_icd10(self, code: str) -> Optional[Dict]:
        """
        Get cached ICD-10 data.
        
        Args:
            code: ICD-10 code
            
        Returns:
            Cached data or None
        """
        key = f"rag:icd10:{code.upper()}"
        return self.get(key)
    
    def cache_drug_interaction(
        self,
        drug_a: str,
        drug_b: str,
        result: Dict
    ) -> bool:
        """
        Cache drug interaction check result.
        
        Args:
            drug_a: First drug name
            drug_b: Second drug name
            result: Interaction check result
            
        Returns:
            True if cached successfully
        """
        # Normalize order for consistent caching
        drugs = sorted([drug_a.lower(), drug_b.lower()])
        key = f"rag:drug_interaction:{drugs[0]}:{drugs[1]}"
        return self.set(key, result, self.TTL_DRUG_INTERACTION)
    
    def get_drug_interaction(
        self,
        drug_a: str,
        drug_b: str
    ) -> Optional[Dict]:
        """
        Get cached drug interaction result.
        
        Args:
            drug_a: First drug name
            drug_b: Second drug name
            
        Returns:
            Cached result or None
        """
        drugs = sorted([drug_a.lower(), drug_b.lower()])
        key = f"rag:drug_interaction:{drugs[0]}:{drugs[1]}"
        return self.get(key)
    
    def cache_rag_search(
        self,
        query: str,
        results: List[Dict],
        collection: str = "default"
    ) -> bool:
        """
        Cache RAG search results.
        
        Args:
            query: Search query
            results: Search results
            collection: Vector store collection name
            
        Returns:
            True if cached successfully
        """
        key = self._make_key(f"search:{collection}", query)
        return self.set(key, results, self.TTL_RAG_SEARCH)
    
    def get_rag_search(
        self,
        query: str,
        collection: str = "default"
    ) -> Optional[List[Dict]]:
        """
        Get cached RAG search results.
        
        Args:
            query: Search query
            collection: Vector store collection name
            
        Returns:
            Cached results or None
        """
        key = self._make_key(f"search:{collection}", query)
        return self.get(key)
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "rag:icd10:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.is_connected:
            return 0
        
        try:
            keys = list(self.redis.scan_iter(match=pattern))
            if keys:
                return self.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Invalidate error: {e}")
        return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        if not self.is_connected:
            return {"connected": False}
        
        try:
            info = self.redis.info(section="stats")
            return {
                "connected": True,
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "keys": self.redis.dbsize(),
            }
        except Exception as e:
            logger.warning(f"Stats error: {e}")
            return {"connected": True, "error": str(e)}


# Global cache instance
_rag_cache: Optional[RAGCache] = None


def get_rag_cache() -> RAGCache:
    """
    Get global RAG cache instance.
    
    Returns:
        RAGCache singleton instance
    """
    global _rag_cache
    if _rag_cache is None:
        _rag_cache = RAGCache()
    return _rag_cache
