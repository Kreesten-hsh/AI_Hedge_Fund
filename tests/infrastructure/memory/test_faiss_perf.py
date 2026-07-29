import time
import shutil
from datetime import datetime, timezone
from decimal import Decimal
import numpy as np
import pytest

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame, Side
from aegis_trade.domain.memory import Experience, MarketFeatures, MarketSession, MemoryCategory
from aegis_trade.infrastructure.memory.faiss_store import FaissVectorStore

def get_dummy_experience(id: str, embedding: tuple[float, ...], category: MemoryCategory):
    features = MarketFeatures(
        1,1,1,1,1,0,0,0,0,MarketSession.OTHER,0,False,0,50,0,0,0,0,0,0,0
    )
    return Experience(
        id=id,
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=Symbol("X", AssetClass.FOREX),
        timeframe=TimeFrame.M1,
        features=features,
        decision_side=Side.LONG,
        pnl=Decimal("0"),
        max_drawdown=Decimal("0"),
        duration_seconds=1,
        category=category,
        embedding=embedding
    )

@pytest.fixture
def temp_faiss_dir(tmp_path):
    d = tmp_path / "faiss_perf"
    yield str(d)
    if d.exists():
        shutil.rmtree(d)

def test_faiss_performance(temp_faiss_dir):
    dim = 25
    store = FaissVectorStore(dimension=dim, storage_dir=temp_faiss_dir)
    
    # Generate 5000 random experiences to simulate a decent memory size
    num_exps = 5000
    np.random.seed(42)
    vectors = np.random.rand(num_exps, dim).astype(np.float32)
    
    # Batch insertion is not implemented in our port yet (we do it one by one)
    # However, for 5000 it should still be fast. Let's test single insertion performance
    t0 = time.perf_counter()
    for i in range(100):
        e = get_dummy_experience(str(i), tuple(vectors[i].tolist()), MemoryCategory.SUCCESS)
        store.save(e)
    t1 = time.perf_counter()
    
    avg_insert_ms = ((t1 - t0) / 100) * 1000
    assert avg_insert_ms < 20.0, f"Average insertion time {avg_insert_ms}ms exceeds 20ms limit"
    
    # Fill the rest silently without persisting each time to speed up the test setup
    for i in range(100, num_exps):
        # We manually add to FAISS to bypass individual persistance overhead for the test setup
        # Our save() method calls _persist() every time. In production a bulk_save or async flush
        # is recommended, but here we just populate to test search performance.
        store.index.add_with_ids(np.array([vectors[i]]), np.array([i], dtype=np.int64))
        store.experiences[i] = get_dummy_experience(str(i), tuple(vectors[i].tolist()), MemoryCategory.FAILURE)
        store.uuid_to_id[str(i)] = i
    store._next_id = num_exps
    store._persist()
    
    # Test Search Performance
    search_vector = tuple(np.random.rand(dim).astype(np.float32).tolist())
    
    t0 = time.perf_counter()
    store.search(search_vector, top_k=200)
    t1 = time.perf_counter()
    
    search_ms = (t1 - t0) * 1000
    assert search_ms < 100.0, f"Search Top-200 time {search_ms}ms exceeds 100ms limit"

