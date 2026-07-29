from datetime import datetime, timezone
from decimal import Decimal
import pytest

from aegis_trade.core.events.bus import InMemoryEventBus
from aegis_trade.domain.core import Symbol, AssetClass, MarketBar, TimeFrame
from aegis_trade.engine.events import (
    MarketEvent, PositionEvent, TradeEvent, ExperienceSavedEvent
)
from aegis_trade.application.memory.manager import MemoryManager
from aegis_trade.application.reflection.builder import ExperienceBuilder
from aegis_trade.application.reflection.pipeline import ReflectionPipeline
from aegis_trade.domain.memory import Experience
from aegis_trade.domain.ports.memory import IVectorStore, IEmbeddingGenerator

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



class EventCatcher:
    def __init__(self):
        self.events = []
    
    def handle(self, event):
        self.events.append(event)


@pytest.fixture
def memory_manager():
    return MemoryManager(MockVectorStore(), MockEmbedding())

@pytest.fixture
def builder():
    return ExperienceBuilder(MockEmbedding())

@pytest.fixture
def pipeline(memory_manager, builder):
    event_bus = InMemoryEventBus()
    return ReflectionPipeline(event_bus, memory_manager, builder), event_bus

def test_reflection_pipeline_flow(pipeline, memory_manager):
    pipe, bus = pipeline
    
    catcher = EventCatcher()
    bus.subscribe("memory", catcher)
    
    symbol = Symbol("EURUSD", AssetClass.FOREX)
    t0 = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    t1 = datetime(2023, 1, 1, 13, 0, tzinfo=timezone.utc)
    
    # 1. Market Event
    bar = MarketBar(
        symbol=symbol, timeframe=TimeFrame.M1, timestamp=t0,
        open=Decimal("1.10"), high=Decimal("1.11"), low=Decimal("1.09"), close=Decimal("1.105"), volume=Decimal("100")
    )
    bus.publish(MarketEvent(timestamp=t0, bar=bar))
    
    # 2. Position Opened
    bus.publish(PositionEvent(
        timestamp=t0, symbol=symbol, action="opened", volume=Decimal("1"), average_price=Decimal("1.105")
    ))
    
    # 3. Trade Closed
    bus.publish(TradeEvent(
        timestamp=t1, trade_id="tr-1", symbol=symbol, action="closed", realized_pnl=Decimal("50.0")
    ))
    
    # Verify memory saved
    assert len(memory_manager._vector_store.saved) == 1
    exp = memory_manager._vector_store.saved[0]
    
    assert exp.pnl == Decimal("50.0")
    assert exp.symbol == symbol
    assert exp.duration_seconds == 3600
    
    # Verify Audit Event published
    assert len(catcher.events) == 1
    assert isinstance(catcher.events[0], ExperienceSavedEvent)
    assert catcher.events[0].experience_id == exp.id
    
    # 4. Position Updated (Coverage for elif updated)
    bus.publish(PositionEvent(
        timestamp=t1, symbol=symbol, action="updated", volume=Decimal("1"), average_price=Decimal("1.105")
    ))
    
def test_reflection_pipeline_exception_handling(pipeline):
    pipe, bus = pipeline
    
    catcher = EventCatcher()
    bus.subscribe("memory", catcher)
    
    symbol = Symbol("EURUSD", AssetClass.FOREX)
    t0 = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    t1 = datetime(2023, 1, 1, 13, 0, tzinfo=timezone.utc)
    
    bar = MarketBar(
        symbol=symbol, timeframe=TimeFrame.M1, timestamp=t0,
        open=Decimal("1.10"), high=Decimal("1.11"), low=Decimal("1.09"), close=Decimal("1.105"), volume=Decimal("100")
    )
    bus.publish(MarketEvent(timestamp=t0, bar=bar))
    
    bus.publish(PositionEvent(
        timestamp=t0, symbol=symbol, action="opened", volume=Decimal("1"), average_price=Decimal("1.105")
    ))
    
    # Force an exception by passing an invalid event or patching a component
    # Actually, if we pass a TradeEvent with invalid pnl type, Decimal will raise error, or we can just mock extractor
    pipe._extractor.extract = None # This will raise TypeError when called
    
    bus.publish(TradeEvent(
        timestamp=t1, trade_id="tr-error", symbol=symbol, action="closed", realized_pnl=Decimal("50.0")
    ))
    
    # Should publish ExperienceRejectedEvent due to exception
    assert len(catcher.events) == 1
    assert catcher.events[0].event_type == "memory"
    assert hasattr(catcher.events[0], "reason")

    
def test_reflection_pipeline_missing_observation(pipeline):
    pipe, bus = pipeline
    
    catcher = EventCatcher()
    bus.subscribe("memory", catcher)
    
    # Trade Closed without Position Opened
    bus.publish(TradeEvent(
        timestamp=datetime(2023, 1, 1, 13, 0, tzinfo=timezone.utc),
        trade_id="tr-2", 
        symbol=Symbol("GBPUSD", AssetClass.FOREX), 
        action="closed", 
        realized_pnl=Decimal("10.0")
    ))
    
    assert len(catcher.events) == 1
    assert catcher.events[0].event_type == "memory"
    assert "reason" in dir(catcher.events[0]) # Should be ExperienceRejectedEvent
