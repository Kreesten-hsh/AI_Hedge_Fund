import os
import shutil
from datetime import datetime, timezone
from decimal import Decimal
import pytest

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame, Side
from aegis_trade.domain.memory import Experience, MarketFeatures, MarketSession, MemoryCategory
from aegis_trade.infrastructure.memory.faiss_store import FaissVectorStore

@pytest.fixture
def temp_faiss_dir(tmp_path):
    d = tmp_path / "faiss_test"
    yield str(d)
    if d.exists():
        shutil.rmtree(d)

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

def test_faiss_store_save_and_search(temp_faiss_dir):
    store = FaissVectorStore(dimension=3, storage_dir=temp_faiss_dir)
    
    e1 = get_dummy_experience("1", (1.0, 0.0, 0.0), MemoryCategory.SUCCESS)
    e2 = get_dummy_experience("2", (0.0, 1.0, 0.0), MemoryCategory.FAILURE)
    e3 = get_dummy_experience("3", (0.0, 0.0, 1.0), MemoryCategory.SUCCESS)
    
    store.save(e1)
    store.save(e2)
    store.save(e3)
    
    assert store.get_stats()["total_vectors"] == 3
    
    # Search close to e1
    results = store.search((0.9, 0.1, 0.0), top_k=2)
    assert len(results) == 2
    assert results[0].experience.id == "1"
    
    # Search filtering by SUCCESS
    success_results = store.search((0.0, 0.9, 0.1), top_k=10, categories=[MemoryCategory.SUCCESS])
    # The closest point in general is e2 (failure), but we filtered by SUCCESS, so it should return e3 then e1
    assert len(success_results) == 2
    assert success_results[0].experience.id == "3"
    assert success_results[1].experience.id == "1"

def test_faiss_store_delete_and_archive(temp_faiss_dir):
    store = FaissVectorStore(dimension=3, storage_dir=temp_faiss_dir)
    e1 = get_dummy_experience("1", (1.0, 0.0, 0.0), MemoryCategory.SUCCESS)
    store.save(e1)
    
    assert store.get_stats()["total_vectors"] == 1
    store.delete("1")
    assert store.get_stats()["total_vectors"] == 0
    
    store.save(e1)
    store.archive("1")
    assert store.get_stats()["total_vectors"] == 0
    # verify archive file
    archive_path = os.path.join(temp_faiss_dir, "archive.jsonl")
    assert os.path.exists(archive_path)

def test_faiss_persistence(temp_faiss_dir):
    store1 = FaissVectorStore(dimension=3, storage_dir=temp_faiss_dir)
    e1 = get_dummy_experience("persist_1", (1.0, 0.0, 0.0), MemoryCategory.SUCCESS)
    store1.save(e1)
    
    # Create new instance pointing to same dir
    store2 = FaissVectorStore(dimension=3, storage_dir=temp_faiss_dir)
    assert store2.get_stats()["total_vectors"] == 1
    
    res = store2.search((1.0, 0.0, 0.0), top_k=1)
    assert res[0].experience.id == "persist_1"
