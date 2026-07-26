import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame, MarketBar
from aegis_trade.domain.exceptions.data import PipelineError, ValidationError, DataProviderError
from aegis_trade.infrastructure.data.pipeline import MarketDataPipeline
from aegis_trade.infrastructure.data.cache import MemoryCache
from aegis_trade.infrastructure.data.validator import DataValidator
from aegis_trade.infrastructure.data.normalizer import DataNormalizer
from aegis_trade.infrastructure.data.registry import ProviderRegistry

@pytest.fixture(autouse=True)
def setup_registry():
    # Make sure we don't pollute registry across tests
    ProviderRegistry._registry = {}
    
@pytest.fixture
def pipeline():
    return MarketDataPipeline(
        cache_backend=MemoryCache(),
        validator=DataValidator(),
        normalizer=DataNormalizer()
    )

@pytest.fixture
def dummy_bars():
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    return [
        MarketBar(
            symbol=sym,
            timeframe=TimeFrame.D1,
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            open=Decimal("100.5"),
            high=Decimal("101.0"),
            low=Decimal("100.0"),
            close=Decimal("100.8"),
            volume=Decimal("1000")
        ),
        MarketBar(
            symbol=sym,
            timeframe=TimeFrame.D1,
            timestamp=datetime(2023, 1, 2, tzinfo=timezone.utc),
            open=Decimal("100.8"),
            high=Decimal("101.5"),
            low=Decimal("100.5"),
            close=Decimal("101.2"),
            volume=Decimal("1200")
        )
    ]

def test_pipeline_successful_fetch_and_cache(pipeline, dummy_bars):
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = dummy_bars
    ProviderRegistry.register("mock_provider", lambda **kwargs: mock_provider)
    
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    # 1. First fetch: should hit API
    bars, context = pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end)
    
    assert len(bars) == 2
    assert not context.cache_hit
    assert context.source == "api"
    assert context.provider == "mock_provider"
    mock_provider.fetch_ohlcv.assert_called_once()
    
    # 2. Second fetch: should hit cache
    bars2, context2 = pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end)
    
    assert len(bars2) == 2
    assert context2.cache_hit
    assert context2.source == "cache"
    assert mock_provider.fetch_ohlcv.call_count == 1 # Still 1, didn't call API again

def test_pipeline_validation_error_propagates(pipeline):
    mock_provider = MagicMock()
    
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    
    # Create unordered bars to trigger ValidationError
    unordered_bars = [
        MarketBar(
            symbol=sym,
            timeframe=TimeFrame.D1,
            timestamp=datetime(2023, 1, 2, tzinfo=timezone.utc), # 2nd Jan
            open=Decimal("100.5"), high=Decimal("101.0"), low=Decimal("100.0"), close=Decimal("100.8"), volume=Decimal("1000")
        ),
        MarketBar(
            symbol=sym,
            timeframe=TimeFrame.D1,
            timestamp=datetime(2023, 1, 2, tzinfo=timezone.utc), # Duplicate 2nd Jan!
            open=Decimal("100.8"), high=Decimal("101.5"), low=Decimal("100.5"), close=Decimal("101.2"), volume=Decimal("1200")
        )
    ]
    
    mock_provider.fetch_ohlcv.return_value = unordered_bars
    ProviderRegistry.register("mock_provider", lambda **kwargs: mock_provider)
    
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    # Should raise ValidationError directly, not masked by PipelineError
    with pytest.raises(ValidationError, match="Temporal order violation"):
        pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end, use_cache=False)

def test_pipeline_provider_error_propagates(pipeline):
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.side_effect = DataProviderError("API Rate Limit")
    ProviderRegistry.register("mock_provider", lambda **kwargs: mock_provider)
    
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    with pytest.raises(DataProviderError, match="API Rate Limit"):
        pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end, use_cache=False)
