import json
import redis
from typing import Optional, List, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache for hot data (conversation history, session states)"""

    def __init__(self, url: str = None):
        self.url = url or os.getenv("REDIS_URL", "redis://redis:6379/1")
        self.client = redis.from_url(self.url, decode_responses=True)

    def set(self, key: str, value: Any, ttl: int = 86400):
        """Set a value with TTL (default 24 hours)"""
        try:
            self.client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get a value"""
        try:
            value = self.client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete a key"""
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    def lpush(self, key: str, value: Any, max_length: int = 20):
        """Push to list (left) and trim to max_length"""
        try:
            self.client.lpush(key, json.dumps(value))
            self.client.ltrim(key, 0, max_length - 1)
            return True
        except Exception as e:
            logger.error(f"Redis LPUSH error: {e}")
            return False

    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get list range"""
        try:
            items = self.client.lrange(key, start, end)
            return [json.loads(item) for item in items]
        except Exception as e:
            logger.error(f"Redis LRANGE error: {e}")
            return []

    def expire(self, key: str, ttl: int):
        """Set expiry on key"""
        try:
            self.client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False


# Global instance
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache