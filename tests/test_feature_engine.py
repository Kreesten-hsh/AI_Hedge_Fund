import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame, MarketBar
from aegis_trade.domain.features import FeatureSet, FeatureGroup
from aegis_trade.domain.exceptions.data import FeatureValidationError

from aegis_trade.infrastructure.features.technical_extractor import TechnicalFeatureExtractor
from aegis_trade.infrastructure.features.validator import FeatureValidator
from aegis_trade.infrastructure.features.feature_store import FeatureStore
from aegis_trade.infrastructure.features.cache import FeatureCache
from aegis_trade.infrastructure.features.pipeline import FeaturePipeline

@pytest.fixture
def dummy_symbol():
    return Symbol("BTCUSD", AssetClass.CRYPTO)

@pytest.fixture
def dummy_bars(dummy_symbol):
    # Create 50 bars to compute EMAs and returns
    bars = []
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    for i in range(50):
        close_val = 100 + i
        high_val = max(100, close_val) + 2
        low_val = min(100, close_val) - 2
        bars.append(MarketBar(
            symbol=dummy_symbol,
            timeframe=TimeFrame.D1,
            timestamp=base_time + timedelta(days=i),
            open=Decimal("100"),
            high=Decimal(str(high_val)),
            low=Decimal(str(low_val)),
            close=Decimal(str(close_val)),
            volume=Decimal("1000")
        ))
    return bars

def test_feature_metadata():
    extractor = TechnicalFeatureExtractor()
    meta = extractor.get_metadata()
    assert len(meta) > 10
    names = [m.name for m in meta]
    assert "return_1d" in names
    assert "ema_10" in names
    assert "rsi_14" in names
    assert "macd" in names

def test_technical_extractor(dummy_bars):
    extractor = TechnicalFeatureExtractor()
    features = extractor.extract(dummy_bars)
    
    assert len(features) == 50
    assert isinstance(features[0], FeatureSet)
    
    # 1D Return of close: 101/100 - 1 = 0.01 for i=1
    assert features[1].features["return_1d"] == pytest.approx(0.01)
    
    # EMA 10 logic check
    # The first EMA 10 value is just the close price (100)
    assert features[0].features["ema_10"] == 100.0
    
    # Typical Price: (high + low + close) / 3
    # i=0: (100+100+100)/3 = 100
    assert features[0].features["typical_price"] == 100.0

def test_validator_success(dummy_bars):
    extractor = TechnicalFeatureExtractor()
    features = extractor.extract(dummy_bars)
    validator = FeatureValidator()
    
    # Since we only have 50 bars, and some features like ema_200 might have NaNs (if adjust=True),
    # but pandas ewm with adjust=False starts at first value. 
    # Returns have NaNs at the beginning.
    # Burn-in of 10 should be enough for return_10d.
    validated = validator.validate(features, burn_in_periods=30)
    assert len(validated) == 50

def test_validator_fails_on_nan_after_burn_in(dummy_bars):
    extractor = TechnicalFeatureExtractor()
    features = extractor.extract(dummy_bars)
    
    # Force a NaN at index 35 (after burn-in)
    features[35].features["return_1d"] = float('nan')
    
    validator = FeatureValidator()
    with pytest.raises(FeatureValidationError, match="Unexpected NaN in feature"):
        validator.validate(features, burn_in_periods=30)

def test_validator_fails_on_temporal_violation(dummy_bars):
    extractor = TechnicalFeatureExtractor()
    features = extractor.extract(dummy_bars)
    
    # Break temporal order
    features[5] = features[4]
    
    validator = FeatureValidator()
    with pytest.raises(FeatureValidationError, match="Temporal violation"):
        validator.validate(features, burn_in_periods=30)

def test_feature_store_save_load(tmp_path, dummy_symbol, dummy_bars):
    extractor = TechnicalFeatureExtractor()
    features = extractor.extract(dummy_bars)
    
    store = FeatureStore(data_dir=str(tmp_path))
    
    # Should be None initially
    assert store.get_latest_timestamp(dummy_symbol, TimeFrame.D1) is None
    assert store.load_features(dummy_symbol, TimeFrame.D1) == []
    
    # Save
    store.save_and_merge_features(dummy_symbol, TimeFrame.D1, features)
    
    # Check timestamp
    latest = store.get_latest_timestamp(dummy_symbol, TimeFrame.D1)
    assert latest == features[-1].timestamp
    
    # Load
    loaded = store.load_features(dummy_symbol, TimeFrame.D1)
    assert len(loaded) == 50
    assert loaded[-1].features["ema_10"] == features[-1].features["ema_10"]
    
def test_feature_cache(dummy_symbol, dummy_bars):
    extractor = TechnicalFeatureExtractor()
    features = extractor.extract(dummy_bars)
    
    cache = FeatureCache(default_ttl=60)
    cache.set(dummy_symbol, TimeFrame.D1, features)
    
    cached = cache.get(dummy_symbol, TimeFrame.D1)
    assert cached is not None
    assert len(cached) == 50
    
    cache.invalidate(dummy_symbol, TimeFrame.D1)
    assert cache.get(dummy_symbol, TimeFrame.D1) is None

def test_feature_pipeline(tmp_path, dummy_symbol, dummy_bars):
    # Mock MarketDataPipeline
    mock_market_pipeline = MagicMock()
    mock_market_pipeline.fetch_ohlcv.return_value = (dummy_bars, {})
    
    store = FeatureStore(data_dir=str(tmp_path))
    cache = FeatureCache()
    extractor = TechnicalFeatureExtractor()
    validator = FeatureValidator()
    
    pipeline = FeaturePipeline(
        market_data_pipeline=mock_market_pipeline,
        extractor=extractor,
        validator=validator,
        store=store,
        cache=cache
    )
    
    start = dummy_bars[10].timestamp
    end = dummy_bars[40].timestamp
    
    # Fetch (misses store, fetches from market data)
    features, metrics = pipeline.fetch_features("dummy_provider", dummy_symbol, TimeFrame.D1, start, end, use_cache=True)
    
    assert len(features) == 31 # from index 10 to 40 inclusive
    assert metrics["features_generated"] == 50
    assert metrics["cache_hit"] is False
    
    # Second fetch should hit cache
    features2, metrics2 = pipeline.fetch_features("dummy_provider", dummy_symbol, TimeFrame.D1, start, end, use_cache=True)
    assert metrics2["cache_hit"] is True
    assert len(features2) == 31
    assert mock_market_pipeline.fetch_ohlcv.call_count == 1
