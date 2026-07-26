import pytest
from aegis_trade.infrastructure.cache.decision_cache import DecisionCache

def test_decision_cache_hit_and_miss():
    cache = DecisionCache()
    context = {"agent_capability": "macro", "prompt": "test prompt"}
    
    # Miss
    result1 = cache.get(context)
    assert result1 is None
    assert cache.misses == 1
    assert cache.hits == 0
    
    # Set
    cache.set(context, "some_decision")
    
    # Hit
    result2 = cache.get(context)
    assert result2 == "some_decision"
    assert cache.hits == 1
    assert cache.misses == 1

def test_decision_cache_deterministic_hash():
    cache = DecisionCache()
    
    context1 = {"a": 1, "b": 2}
    context2 = {"b": 2, "a": 1} # Same logical content, different order
    
    cache.set(context1, "decision_a")
    
    # Should hit because hash is sorted and deterministic
    assert cache.get(context2) == "decision_a"
    assert cache.hits == 1

def test_decision_cache_clear():
    cache = DecisionCache()
    context = {"key": "val"}
    cache.set(context, "dec")
    
    assert cache.get(context) == "dec"
    cache.clear()
    
    assert cache.get(context) is None
    assert cache.hits == 0
    assert cache.misses == 1
