from abc import ABC, abstractmethod
from typing import Any, Optional
import hashlib
import json
import time
import threading
import logging

logger = logging.getLogger(__name__)

class CacheBackend(ABC):
    """
    Abstract base class for caching backends.
    Allows swapping between MemoryCache, DiskCache, RedisCache, etc.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass
        
    @abstractmethod
    def invalidate(self, key: str) -> None:
        """Removes a specific key from the cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clears the entire cache."""
        pass
        
    @staticmethod
    def generate_key(prefix: str, **kwargs) -> str:
        """
        Generates a deterministic hash key from the given kwargs.
        """
        sorted_kwargs = {k: str(v) for k, v in sorted(kwargs.items())}
        key_str = json.dumps(sorted_kwargs, sort_keys=True)
        hash_digest = hashlib.md5(key_str.encode("utf-8")).hexdigest()
        return f"{prefix}_{hash_digest}"


class MemoryCache(CacheBackend):
    """
    In-memory cache implementation.
    Institutionally hardened: Thread-safe, implements strict TTL enforcement.
    """

    def __init__(self, default_ttl: int = 3600):
        self._cache = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
        
        # Simple metrics
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if expires_at is None or expires_at > time.time():
                    self.hits += 1
                    return value
                else:
                    # Expired
                    del self._cache[key]
                    logger.debug(f"Cache key {key} expired and removed.")
            
            self.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        actual_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + actual_ttl if actual_ttl > 0 else None
        
        with self._lock:
            self._cache[key] = (value, expires_at)
            
    def invalidate(self, key: str) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0
            logger.info("MemoryCache cleared.")
