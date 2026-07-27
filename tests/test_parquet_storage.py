import os
import pytest
import pandas as pd
from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.domain.core import MarketBar, Symbol, AssetClass, TimeFrame
from aegis_trade.domain.exceptions.data import StorageError
from aegis_trade.infrastructure.data.parquet_storage import ParquetStorage

@pytest.fixture
def temp_dir(tmp_path):
    return str(tmp_path / "market_data")

@pytest.fixture
def symbol():
    return Symbol("DXY", AssetClass.INDICES)

@pytest.fixture
def timeframe():
    return TimeFrame.D1

@pytest.fixture
def sample_bars(symbol, timeframe):
    return [
        MarketBar(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            open=Decimal("100.0"),
            high=Decimal("101.0"),
            low=Decimal("99.0"),
            close=Decimal("100.5"),
            volume=Decimal("1000")
        ),
        MarketBar(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime(2023, 1, 2, tzinfo=timezone.utc),
            open=Decimal("100.5"),
            high=Decimal("102.0"),
            low=Decimal("100.0"),
            close=Decimal("101.5"),
            volume=Decimal("1500")
        )
    ]

def test_directory_creation(temp_dir):
    assert not os.path.exists(temp_dir)
    ParquetStorage(data_dir=temp_dir)
    assert os.path.exists(temp_dir)

def test_load_empty_returns_empty(temp_dir, symbol, timeframe):
    storage = ParquetStorage(data_dir=temp_dir)
    bars = storage.load_bars(symbol, timeframe)
    assert bars == []

def test_get_latest_timestamp_empty(temp_dir, symbol, timeframe):
    storage = ParquetStorage(data_dir=temp_dir)
    latest = storage.get_latest_timestamp(symbol, timeframe)
    assert latest is None

def test_save_and_load_bars(temp_dir, symbol, timeframe, sample_bars):
    storage = ParquetStorage(data_dir=temp_dir)
    returned_bars = storage.save_and_merge_bars(symbol, timeframe, sample_bars)
    
    assert len(returned_bars) == 2
    assert returned_bars[0].timestamp == datetime(2023, 1, 1, tzinfo=timezone.utc)
    
    # Reload from disk
    loaded_bars = storage.load_bars(symbol, timeframe)
    assert len(loaded_bars) == 2
    assert loaded_bars[1].close == Decimal("101.5")

    # Check latest timestamp
    latest = storage.get_latest_timestamp(symbol, timeframe)
    assert latest == datetime(2023, 1, 2, tzinfo=timezone.utc)

def test_delta_merge_no_duplicates(temp_dir, symbol, timeframe, sample_bars):
    storage = ParquetStorage(data_dir=temp_dir)
    storage.save_and_merge_bars(symbol, timeframe, sample_bars)
    
    # Create overlapping bars (update the 2023-01-02 one and add 2023-01-03)
    overlapping_bars = [
        MarketBar(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime(2023, 1, 2, tzinfo=timezone.utc),
            open=Decimal("100.5"),
            high=Decimal("103.0"), # Updated high
            low=Decimal("100.0"),
            close=Decimal("102.5"), # Updated close
            volume=Decimal("2000")
        ),
        MarketBar(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime(2023, 1, 3, tzinfo=timezone.utc),
            open=Decimal("102.5"),
            high=Decimal("104.0"),
            low=Decimal("102.0"),
            close=Decimal("103.5"),
            volume=Decimal("1200")
        )
    ]
    
    merged_bars = storage.save_and_merge_bars(symbol, timeframe, overlapping_bars)
    assert len(merged_bars) == 3
    
    # Check that the overlapping one was updated (kept the last)
    assert merged_bars[1].timestamp == datetime(2023, 1, 2, tzinfo=timezone.utc)
    assert merged_bars[1].high == Decimal("103.0")
    assert merged_bars[1].close == Decimal("102.5")
    
    # Check the new one
    assert merged_bars[2].timestamp == datetime(2023, 1, 3, tzinfo=timezone.utc)

def test_save_empty_list(temp_dir, symbol, timeframe, sample_bars):
    storage = ParquetStorage(data_dir=temp_dir)
    storage.save_and_merge_bars(symbol, timeframe, sample_bars)
    
    # Save empty should just return existing
    bars = storage.save_and_merge_bars(symbol, timeframe, [])
    assert len(bars) == 2

def test_corrupted_parquet_file(temp_dir, symbol, timeframe):
    storage = ParquetStorage(data_dir=temp_dir)
    
    # Create a corrupted file manually
    file_path = storage._get_file_path(symbol, timeframe)
    with open(file_path, "w") as f:
        f.write("corrupted data not parquet")
        
    with pytest.raises(StorageError):
        storage.load_bars(symbol, timeframe)
        
    with pytest.raises(StorageError):
        storage.get_latest_timestamp(symbol, timeframe)
        
    with pytest.raises(StorageError):
        storage.save_and_merge_bars(symbol, timeframe, [
            MarketBar(symbol, timeframe, datetime(2023, 1, 1, tzinfo=timezone.utc), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1"))
        ])
