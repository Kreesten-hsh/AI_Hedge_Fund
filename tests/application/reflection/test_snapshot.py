from datetime import datetime, timezone
import pytest
from decimal import Decimal

from aegis_trade.domain.core import Symbol, AssetClass, MarketBar, TimeFrame
from aegis_trade.engine.events import MarketEvent
from aegis_trade.application.reflection.snapshot import MarketSnapshotBuilder


@pytest.fixture
def snapshot_builder():
    return MarketSnapshotBuilder()

def test_market_snapshot_builder(snapshot_builder):
    symbol = Symbol("BTCUSD", AssetClass.CRYPTO)
    timestamp = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    bar1 = MarketBar(
        symbol=symbol,
        timeframe=TimeFrame.M1,
        timestamp=timestamp,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("1000")
    )
    
    event1 = MarketEvent(timestamp=timestamp, bar=bar1)
    snapshot_builder.on_market_event(event1)
    
    snapshot = snapshot_builder.get_snapshot(symbol)
    assert snapshot is not None
    assert snapshot.latest_bar.close == Decimal("105")
    assert len(snapshot.history) == 1
    
    # Verify immutability of the retrieved snapshot
    bar2 = MarketBar(
        symbol=symbol,
        timeframe=TimeFrame.M1,
        timestamp=timestamp,
        open=Decimal("105"),
        high=Decimal("115"),
        low=Decimal("95"),
        close=Decimal("112"),
        volume=Decimal("2000")
    )
    event2 = MarketEvent(timestamp=timestamp, bar=bar2)
    snapshot_builder.on_market_event(event2)
    
    # Original snapshot should not have changed
    assert snapshot.latest_bar.close == Decimal("105")
    assert len(snapshot.history) == 1
    
    # New snapshot should have the latest data
    snapshot2 = snapshot_builder.get_snapshot(symbol)
    assert snapshot2.latest_bar.close == Decimal("112")
    assert len(snapshot2.history) == 2
    
def test_market_snapshot_empty(snapshot_builder):
    symbol = Symbol("EURUSD", AssetClass.FOREX)
    assert snapshot_builder.get_snapshot(symbol) is None
