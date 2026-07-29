from datetime import datetime, timezone
from decimal import Decimal
import pytest

from aegis_trade.domain.core import Symbol, AssetClass, Side, TimeFrame
from aegis_trade.domain.memory import MarketFeatures, MarketSession, MemoryCategory
from aegis_trade.application.reflection.builder import ExperienceBuilder
from aegis_trade.domain.ports.memory import IEmbeddingGenerator


class MockEmbeddingGenerator(IEmbeddingGenerator):
    def generate(self, features: MarketFeatures) -> tuple[float, ...]:
        return (0.1, 0.2, 0.3)


@pytest.fixture
def builder():
    return ExperienceBuilder(MockEmbeddingGenerator())

def get_dummy_features():
    return MarketFeatures(
        1,1,1,1,1,0,0,0,0,MarketSession.OTHER,0,False,0,50,0,0,0,0,0,0,0
    )

def test_experience_builder_success(builder):
    features = get_dummy_features()
    
    exp = builder.build(
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=Symbol("EURUSD", AssetClass.FOREX),
        timeframe=TimeFrame.H1,
        decision_side=Side.LONG,
        features=features,
        pnl=Decimal("15.0"),
        max_drawdown=Decimal("0.5"),
        duration_seconds=3600
    )
    
    assert exp.id is not None
    assert exp.category == MemoryCategory.SUCCESS
    assert exp.embedding == (0.1, 0.2, 0.3)
    assert exp.decision_side == Side.LONG
    
def test_experience_builder_failure(builder):
    exp = builder.build(
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=Symbol("EURUSD", AssetClass.FOREX),
        timeframe=TimeFrame.H1,
        decision_side=Side.SHORT,
        features=get_dummy_features(),
        pnl=Decimal("-5.0"),
        max_drawdown=Decimal("6.0"),
        duration_seconds=3600
    )
    
    assert exp.category == MemoryCategory.FAILURE

def test_experience_builder_metadata_override(builder):
    exp = builder.build(
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=Symbol("EURUSD", AssetClass.FOREX),
        timeframe=TimeFrame.H1,
        decision_side=Side.SHORT,
        features=get_dummy_features(),
        pnl=Decimal("15.0"),
        max_drawdown=Decimal("0.5"),
        duration_seconds=3600,
        metadata={"force_category": "exceptional", "custom_tag": "test"}
    )
    
    assert exp.category == MemoryCategory.EXCEPTIONAL
    assert exp.metadata["custom_tag"] == "test"
    
def test_experience_builder_metadata_override_invalid(builder):
    exp = builder.build(
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=Symbol("EURUSD", AssetClass.FOREX),
        timeframe=TimeFrame.H1,
        decision_side=Side.SHORT,
        features=get_dummy_features(),
        pnl=Decimal("15.0"),
        max_drawdown=Decimal("0.5"),
        duration_seconds=3600,
        metadata={"force_category": "invalid_category"}
    )
    # Should fallback to actual performance (SUCCESS)
    assert exp.category == MemoryCategory.SUCCESS

def test_experience_builder_near_miss_and_unknown(builder):
    exp1 = builder.build(
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=Symbol("EURUSD", AssetClass.FOREX),
        timeframe=TimeFrame.H1,
        decision_side=Side.SHORT,
        features=get_dummy_features(),
        pnl=Decimal("-1.0"),
        max_drawdown=Decimal("1.0"),
        duration_seconds=3600
    )
    assert exp1.category == MemoryCategory.NEAR_MISS
    
    exp2 = builder.build(
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=Symbol("EURUSD", AssetClass.FOREX),
        timeframe=TimeFrame.H1,
        decision_side=Side.SHORT,
        features=get_dummy_features(),
        pnl=Decimal("1.0"),
        max_drawdown=Decimal("3.0"),
        duration_seconds=3600
    )
    assert exp2.category == MemoryCategory.UNKNOWN
