import pytest
import time
import threading
from aegis_trade.infrastructure.data.cache import MemoryCache

def test_memory_cache_set_get():
    cache = MemoryCache(default_ttl=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.hits == 1
    assert cache.misses == 0

def test_memory_cache_ttl_expiration():
    cache = MemoryCache(default_ttl=1)
    cache.set("key1", "value1", ttl=1)
    assert cache.get("key1") == "value1"
    time.sleep(1.1)
    # Should expire
    assert cache.get("key1") is None
    assert cache.misses == 1

def test_memory_cache_invalidate_and_clear():
    cache = MemoryCache(default_ttl=60)
    cache.set("key1", "val1")
    cache.set("key2", "val2")
    
    cache.invalidate("key1")
    assert cache.get("key1") is None
    assert cache.get("key2") == "val2"
    
    cache.clear()
    assert cache.get("key2") is None
    assert cache.hits == 0 # reset by clear
    assert cache.misses == 1 # incremented by getting key2 after clear

def test_memory_cache_concurrency():
    cache = MemoryCache(default_ttl=10)
    
    def worker(worker_id):
        for i in range(100):
            key = f"key_{worker_id}_{i}"
            cache.set(key, i)
            val = cache.get(key)
            assert val == i
            
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    assert cache.hits == 1000
    assert cache.misses == 0
