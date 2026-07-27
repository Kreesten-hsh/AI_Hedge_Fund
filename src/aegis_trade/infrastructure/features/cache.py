import time
import threading
from typing import List, Optional
import hashlib

from aegis_trade.domain.core import Symbol, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.exceptions.data import CacheError


class FeatureCache:
    """
    Thread-safe in-memory cache for FeatureSets.
    Uses TTL for cache expiration and a hashed key strategy.
    """

    def __init__(self, default_ttl: int = 300):
        self._cache = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl

    def _generate_key(self, symbol: Symbol, timeframe: TimeFrame) -> str:
        # A simple deterministic hash based on symbol and timeframe
        key_str = f"{symbol.name}_{symbol.asset_class.value}_{timeframe.value}"
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()

    def get(self, symbol: Symbol, timeframe: TimeFrame) -> Optional[List[FeatureSet]]:
        """Retrieves cached features if not expired."""
        key = self._generate_key(symbol, timeframe)
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() < entry["expires_at"]:
                    return entry["data"]
                else:
                    del self._cache[key]
        return None

    def set(self, symbol: Symbol, timeframe: TimeFrame, features: List[FeatureSet], ttl: Optional[int] = None) -> None:
        """Stores features in the cache with an optional custom TTL."""
        if not features:
            return
            
        key = self._generate_key(symbol, timeframe)
        expires_at = time.time() + (ttl if ttl is not None else self.default_ttl)
        
        with self._lock:
            self._cache[key] = {
                "data": features,
                "expires_at": expires_at
            }

    def invalidate(self, symbol: Symbol, timeframe: TimeFrame) -> None:
        """Removes a specific entry from the cache."""
        key = self._generate_key(symbol, timeframe)
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        """Clears all cached features."""
        with self._lock:
            self._cache.clear()
