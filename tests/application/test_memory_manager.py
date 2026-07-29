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

def test_save_experience(manager):
    symbol = Symbol("EURUSD", AssetClass.FOREX)
    features = get_dummy_features()
    
    experience = Experience(
        id="test-123",
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=symbol,
        timeframe=TimeFrame.M1,
        features=features,
        decision_side=Side.LONG,
        pnl=Decimal("15.0"),
        max_drawdown=Decimal("0.5"),
        duration_seconds=120,
        category=MemoryCategory.SUCCESS,
        embedding=(0.1, 0.2)
    )
    
    exp_id = manager.save_experience(experience)
    
    assert exp_id == "test-123"
    assert len(manager._vector_store.saved) == 1
    exp = manager._vector_store.saved[0]
    assert exp.id == "test-123"

def test_manager_methods(manager):
    # Test convenience methods
    manager.search_failure_patterns(get_dummy_features(), 10)
    manager.search_success_patterns(get_dummy_features(), 10)
    manager.get_statistics()
    manager.delete_experience("1")
    manager.archive_experience("1")
