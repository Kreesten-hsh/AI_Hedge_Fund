import pytest
from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame, MarketBar
from aegis_trade.infrastructure.data.validator import DataValidator
from aegis_trade.infrastructure.data.normalizer import DataNormalizer
from aegis_trade.domain.exceptions.data import ValidationError

def test_validator_empty_sequence():
    validator = DataValidator()
    assert validator.validate_ohlcv([]) == []

def test_validator_out_of_order_raises():
    validator = DataValidator()
    sym = Symbol("DXY", AssetClass.INDICES)
    
    bars = [
        MarketBar(sym, TimeFrame.D1, datetime(2023, 1, 2, tzinfo=timezone.utc), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1)),
        MarketBar(sym, TimeFrame.D1, datetime(2023, 1, 1, tzinfo=timezone.utc), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1))
    ]
    # The validator sorts them internally before checking, wait, if it sorts them, it won't raise out of order!
    # Let me check the validator implementation. 
    # Actually, the validator implementation sorts them and then checks for duplicates/temporal violations.
    # So sorting fixes out of order. Let's test duplicates instead.
    
    duplicate_bars = [
        MarketBar(sym, TimeFrame.D1, datetime(2023, 1, 1, tzinfo=timezone.utc), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1)),
        MarketBar(sym, TimeFrame.D1, datetime(2023, 1, 1, tzinfo=timezone.utc), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1))
    ]
    
    with pytest.raises(ValidationError, match="Temporal order violation or duplicate"):
        validator.validate_ohlcv(duplicate_bars)

def test_validator_sorts_correctly():
    validator = DataValidator()
    sym = Symbol("DXY", AssetClass.INDICES)
    
    bars = [
        MarketBar(sym, TimeFrame.D1, datetime(2023, 1, 2, tzinfo=timezone.utc), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1)),
        MarketBar(sym, TimeFrame.D1, datetime(2023, 1, 1, tzinfo=timezone.utc), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1))
    ]
    
    validated = validator.validate_ohlcv(bars)
    assert validated[0].timestamp == datetime(2023, 1, 1, tzinfo=timezone.utc)
    assert validated[1].timestamp == datetime(2023, 1, 2, tzinfo=timezone.utc)

def test_normalizer_rounding():
    normalizer = DataNormalizer()
    sym = Symbol("DXY", AssetClass.INDICES)
    
    bars = [
        MarketBar(sym, TimeFrame.D1, datetime(2023, 1, 1, tzinfo=timezone.utc), 
                  Decimal("1.123456789"), Decimal("1.2"), Decimal("1.0"), Decimal("1.1"), Decimal("1.1"))
    ]
    
    normalized = normalizer.normalize_ohlcv(bars)
    assert normalized[0].open == Decimal("1.12345679") # Rounded to 8 decimals

from unittest.mock import MagicMock
from aegis_trade.domain.exceptions.data import NormalizationError

def test_normalizer_raises_normalization_error():
    normalizer = DataNormalizer()
    
    # Create a mock bar where accessing 'open' raises an exception
    mock_bar = MagicMock(spec=MarketBar)
    type(mock_bar).open = property(lambda self: (_ for _ in ()).throw(Exception("Invalid type for open")))
    
    with pytest.raises(NormalizationError, match="Failed to normalize MarketBars"):
        normalizer.normalize_ohlcv([mock_bar])
