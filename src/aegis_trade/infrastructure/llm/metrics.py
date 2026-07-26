import time
import json
import logging
from typing import Dict, Any, Optional

# Structured logger for LLM infrastructure
llm_logger = logging.getLogger("aegis.infrastructure.llm")
llm_logger.setLevel(logging.INFO)

# Avoid adding multiple handlers if re-imported
if not llm_logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    llm_logger.addHandler(ch)


class LLMMetrics:
    """
    Tracks inference timing, cache hits/misses, and logs structured JSON.
    """
    _instance = None
    
    def __init__(self):
        self.total_calls = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_duration_ms = 0.0
        self.max_duration_ms = 0.0
        self.tokens_estimated = 0
        
    @classmethod
    def get_instance(cls) -> 'LLMMetrics':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_call(
        self, 
        provider: str, 
        model: str, 
        profile: str,
        duration_ms: float, 
        cache_hit: bool, 
        success: bool,
        tokens: int = 0
    ) -> None:
        
        self.total_calls += 1
        self.total_duration_ms += duration_ms
        if duration_ms > self.max_duration_ms:
            self.max_duration_ms = duration_ms
            
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            
        self.tokens_estimated += tokens
        
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "provider": provider,
            "model": model,
            "profile": profile,
            "duration_ms": round(duration_ms, 2),
            "cache_hit": cache_hit,
            "success": success,
            "tokens_estimated": tokens
        }
        
        # Log as structured JSON
        llm_logger.info(json.dumps(log_entry))
        
    def get_summary(self) -> Dict[str, Any]:
        avg_latency = self.total_duration_ms / self.total_calls if self.total_calls > 0 else 0.0
        return {
            "total_calls": self.total_calls,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "average_latency_ms": round(avg_latency, 2),
            "max_duration_ms": round(self.max_duration_ms, 2),
            "tokens_estimated": self.tokens_estimated
        }
