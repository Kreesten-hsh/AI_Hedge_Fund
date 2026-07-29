from datetime import datetime, timezone
from decimal import Decimal
import pytest

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame, Side
from aegis_trade.domain.memory import (
    Experience, MarketFeatures, MarketSession, MemoryCategory, SearchResult
)
from aegis_trade.domain.ports.memory import IVectorStore, IEmbeddingGenerator
from aegis_trade.application.memory.manager import MemoryManager

class MockVectorStore(IVectorStore):
    def __init__(self):
        self.saved = []
    
    def save(self, experience: Experience) -> None:
        self.saved.append(experience)
        
    def search(self, embedding, top_k=200, categories=None):
        return []
        
    def delete(self, experience_id):
        pass
        
    def archive(self, experience_id):
        pass
        
    def get_stats(self):
        return {}

class MockEmbedding(IEmbeddingGenerator):
    def generate(self, features):
        return (0.1, 0.2)

@pytest.fixture
def manager():
    return MemoryManager(MockVectorStore(), MockEmbedding())

def get_dummy_features():
    return MarketFeatures(
        1,1,1,1,1,0,0,0,0,MarketSession.OTHER,0,False,0,50,0,0,0,0,0,0,0
    )

def test_categorization_success(manager):
    cat = manager._determine_category(Decimal("10.0"), Decimal("1.0"), {})
    assert cat == MemoryCategory.SUCCESS

def test_categorization_failure(manager):
    cat = manager._determine_category(Decimal("-5.0"), Decimal("1.0"), {})
    assert cat == MemoryCategory.FAILURE
    
    cat2 = manager._determine_category(Decimal("1.0"), Decimal("6.0"), {})
    assert cat2 == MemoryCategory.FAILURE

def test_categorization_near_miss(manager):
    cat = manager._determine_category(Decimal("-0.5"), Decimal("1.0"), {})
    assert cat == MemoryCategory.NEAR_MISS

def test_categorization_metadata_override(manager):
    cat = manager._determine_category(Decimal("10.0"), Decimal("1.0"), {"force_category": "exceptional"})
    assert cat == MemoryCategory.EXCEPTIONAL

def test_save_experience(manager):
    symbol = Symbol("EURUSD", AssetClass.FOREX)
    features = get_dummy_features()
    
    exp_id = manager.save_experience(
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=symbol,
        timeframe=TimeFrame.M1,
        decision_side=Side.LONG,
        features=features,
        pnl=Decimal("15.0"),
        max_drawdown=Decimal("0.5"),
        duration_seconds=120
    )
    
    assert exp_id is not None
    assert len(manager._vector_store.saved) == 1
    exp = manager._vector_store.saved[0]
    assert exp.id == exp_id
    assert exp.category == MemoryCategory.SUCCESS
    assert exp.embedding == (0.1, 0.2)

def test_manager_methods(manager):
    # Test convenience methods
    manager.search_failure_patterns(get_dummy_features(), 10)
    manager.search_success_patterns(get_dummy_features(), 10)
    manager.get_statistics()
    manager.delete_experience("1")
    manager.archive_experience("1")
    
    # Test category fallback (pnl=1.0, drawdown=3.0 -> not success, not failure, not near_miss)
    cat = manager._determine_category(Decimal("1.0"), Decimal("3.0"), {"force_category": "invalid_cat"})
    assert cat == MemoryCategory.UNKNOWN
