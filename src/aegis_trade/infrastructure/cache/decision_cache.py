import hashlib
import json
from typing import Any, Dict, Optional

class DecisionCache:
    """
    Generic caching layer for structured decisions based on context hash.
    Independent of LLM logic. Can be used by Council, RiskEngine, etc.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self.hits = 0
        self.misses = 0

    def _generate_hash(self, context: Dict[str, Any]) -> str:
        """
        Creates a deterministic hash of the context dictionary.
        """
        # Ensure we only hash JSON-serializable structures
        serialized = json.dumps(context, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    def get(self, context: Dict[str, Any]) -> Optional[Any]:
        """
        Retrieves a cached decision if the exact context has been seen before.
        """
        key = self._generate_hash(context)
        if key in self._cache:
            self.hits += 1
            return self._cache[key]
            
        self.misses += 1
        return None

    def set(self, context: Dict[str, Any], decision: Any) -> None:
        """
        Stores a decision in the cache for a given context.
        """
        key = self._generate_hash(context)
        self._cache[key] = decision

    def clear(self):
        """Clears the cache."""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
        
    def get_metrics(self) -> Dict[str, int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self._cache)
        }
