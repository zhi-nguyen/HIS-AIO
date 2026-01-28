"""
Redis-based Agent Memory Service for managing short-term conversation history.

This service provides a sliding window of recent messages for LangGraph agents,
replacing expensive database queries with fast in-memory Redis operations.
"""
import json
import redis
from typing import List, Dict, Any, Optional
from django.conf import settings


class AgentMemoryService:
    """
    Manages short-term conversation memory for AI agents using Redis.
    
    Uses Redis Lists to store messages with a sliding window approach.
    Keying strategy: agent:memory:{thread_id}
    
    Example usage:
        memory = AgentMemoryService()
        memory.add_message("thread-123", {"role": "user", "content": "Hello"})
        history = memory.get_history("thread-123", limit=20)
    """
    
    def __init__(self, 
                 host: Optional[str] = None, 
                 port: Optional[int] = None, 
                 db: Optional[int] = None,
                 ttl: Optional[int] = None):
        """
        Initialize Redis connection.
        
        Args:
            host: Redis host (defaults to settings.REDIS_HOST or 'localhost')
            port: Redis port (defaults to settings.REDIS_PORT or 6379)
            db: Redis database number (defaults to settings.REDIS_DB or 0)
            ttl: Time-to-live for memory keys in seconds (defaults to 24 hours)
        """
        self.host = host or getattr(settings, 'REDIS_HOST', 'localhost')
        self.port = port or getattr(settings, 'REDIS_PORT', 6379)
        self.db = db or getattr(settings, 'REDIS_DB', 0)
        self.ttl = ttl or getattr(settings, 'REDIS_AGENT_MEMORY_TTL', 86400)  # 24 hours default
        
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True
        )
    
    def _get_key(self, thread_id: str) -> str:
        """Generate Redis key for a conversation thread."""
        return f"agent:memory:{thread_id}"
    
    def add_message(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """
        Add a message to the conversation history.
        
        Args:
            thread_id: Unique identifier for the conversation thread
            message: Message dictionary (should contain 'role' and 'content' at minimum)
        
        Returns:
            True if successful, False otherwise
        
        Example:
            memory.add_message("thread-123", {
                "role": "user",
                "content": "What are my lab results?",
                "timestamp": "2026-01-28T21:30:00"
            })
        """
        try:
            key = self._get_key(thread_id)
            message_json = json.dumps(message, ensure_ascii=False)
            
            # Add message to the right of the list (most recent)
            self.client.rpush(key, message_json)
            
            # Set TTL to auto-expire old conversations
            self.client.expire(key, self.ttl)
            
            return True
        except Exception as e:
            print(f"Error adding message to Redis: {e}")
            return False
    
    def get_history(self, thread_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history with a sliding window.
        
        Args:
            thread_id: Unique identifier for the conversation thread
            limit: Maximum number of recent messages to retrieve (default: 20)
        
        Returns:
            List of message dictionaries, ordered from oldest to newest
        
        Example:
            history = memory.get_history("thread-123", limit=20)
            # Returns: [{"role": "user", "content": "..."}, {...}, ...]
        """
        try:
            key = self._get_key(thread_id)
            
            # Get the last N messages (sliding window)
            # LRANGE with negative indices: -limit gets last N items
            messages_json = self.client.lrange(key, -limit, -1)
            
            # Parse JSON messages
            messages = [json.loads(msg) for msg in messages_json]
            
            return messages
        except Exception as e:
            print(f"Error retrieving history from Redis: {e}")
            return []
    
    def clear_history(self, thread_id: str) -> bool:
        """
        Delete all conversation history for a thread.
        
        Args:
            thread_id: Unique identifier for the conversation thread
        
        Returns:
            True if successful, False otherwise
        
        Example:
            memory.clear_history("thread-123")
        """
        try:
            key = self._get_key(thread_id)
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"Error clearing history from Redis: {e}")
            return False
    
    def get_message_count(self, thread_id: str) -> int:
        """
        Get the total number of messages in a thread.
        
        Args:
            thread_id: Unique identifier for the conversation thread
        
        Returns:
            Number of messages in the thread
        """
        try:
            key = self._get_key(thread_id)
            return self.client.llen(key)
        except Exception as e:
            print(f"Error getting message count from Redis: {e}")
            return 0
    
    def trim_history(self, thread_id: str, max_messages: int = 20) -> bool:
        """
        Trim conversation history to keep only the most recent messages.
        
        This helps prevent unbounded memory growth for long conversations.
        
        Args:
            thread_id: Unique identifier for the conversation thread
            max_messages: Maximum number of messages to keep
        
        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_key(thread_id)
            # Keep only the last max_messages
            self.client.ltrim(key, -max_messages, -1)
            return True
        except Exception as e:
            print(f"Error trimming history in Redis: {e}")
            return False
    
    def ping(self) -> bool:
        """
        Test Redis connection.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            return self.client.ping()
        except Exception as e:
            print(f"Redis connection error: {e}")
            return False
