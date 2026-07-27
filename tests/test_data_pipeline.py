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
    mock_storage = MagicMock()
    mock_storage.get_latest_timestamp.return_value = None
    
    saved_bars = []
    def mock_save(*args, **kwargs):
        bars = args[2] if len(args) > 2 else kwargs.get('new_bars', [])
        saved_bars.extend(bars)
        return saved_bars
        
    def mock_load(*args, **kwargs):
        return saved_bars
        
    mock_storage.save_and_merge_bars.side_effect = mock_save
    mock_storage.load_bars.side_effect = mock_load
    
    return MarketDataPipeline(
        cache_backend=MemoryCache(),
        validator=DataValidator(),
        normalizer=DataNormalizer(),
        storage=mock_storage
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

def test_pipeline_cache_get_error(pipeline, dummy_bars):
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = dummy_bars
    ProviderRegistry.register("mock_provider", lambda **kwargs: mock_provider)
    
    pipeline.cache.get = MagicMock(side_effect=Exception("Redis connection lost"))
    
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    bars, context = pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end)
    
    assert len(bars) == 2
    assert context.source == "api"

def test_pipeline_provider_unexpected_error(pipeline):
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.side_effect = Exception("Unknown provider crash")
    ProviderRegistry.register("mock_provider", lambda **kwargs: mock_provider)
    
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    with pytest.raises(PipelineError, match="Unexpected ingestion failure: Unknown provider crash"):
        pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end, use_cache=False)

def test_pipeline_provider_empty_data(pipeline):
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = []
    ProviderRegistry.register("mock_provider", lambda **kwargs: mock_provider)
    
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    bars, context = pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end, use_cache=False)
    assert bars == []
    assert not context.cache_hit
    assert context.source == "api"

def test_pipeline_validator_unexpected_error(pipeline, dummy_bars):
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = dummy_bars
    ProviderRegistry.register("mock_provider", lambda **kwargs: mock_provider)
    
    pipeline.validator.validate_ohlcv = MagicMock(side_effect=Exception("Validator crash"))
    
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    with pytest.raises(PipelineError, match="Unexpected validation failure: Validator crash"):
        pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end, use_cache=False)

from aegis_trade.domain.exceptions.data import NormalizationError

def test_pipeline_normalizer_normalization_error(pipeline, dummy_bars):
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = dummy_bars
    ProviderRegistry.register("mock_provider", lambda **kwargs: mock_provider)
    
    pipeline.normalizer.normalize_ohlcv = MagicMock(side_effect=NormalizationError("Missing volume column"))
    
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    with pytest.raises(NormalizationError, match="Missing volume column"):
        pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end, use_cache=False)

def test_pipeline_normalizer_unexpected_error(pipeline, dummy_bars):
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = dummy_bars
    ProviderRegistry.register("mock_provider", lambda **kwargs: mock_provider)
    
    pipeline.normalizer.normalize_ohlcv = MagicMock(side_effect=Exception("Normalizer crash"))
    
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    with pytest.raises(PipelineError, match="Unexpected normalization failure: Normalizer crash"):
        pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end, use_cache=False)

def test_pipeline_cache_set_error(pipeline, dummy_bars):
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = dummy_bars
    ProviderRegistry.register("mock_provider", lambda **kwargs: mock_provider)
    
    pipeline.cache.set = MagicMock(side_effect=Exception("Disk full"))
    
    sym = Symbol(name="DXY", asset_class=AssetClass.INDICES)
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 1, 2, tzinfo=timezone.utc)
    
    bars, context = pipeline.fetch_ohlcv("mock_provider", sym, TimeFrame.D1, start, end, use_cache=True)
    
    assert len(bars) == 2
    assert context.source == "api"
