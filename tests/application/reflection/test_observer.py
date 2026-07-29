from datetime import datetime, timezone
from decimal import Decimal
import pytest

from aegis_trade.domain.core import Symbol, AssetClass, MarketBar, TimeFrame
from aegis_trade.engine.events import PositionEvent, TradeEvent
from aegis_trade.application.reflection.observer import TradeObserver


@pytest.fixture
def observer():
    return TradeObserver()

def test_trade_observer_lifecycle(observer):
    symbol = Symbol("AAPL", AssetClass.EQUITIES)
    timestamp = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    snapshot = MarketBar(
        symbol=symbol,
        timeframe=TimeFrame.M1,
        timestamp=timestamp,
        open=Decimal("150"),
        high=Decimal("155"),
        low=Decimal("149"),
        close=Decimal("152"),
        volume=Decimal("1000")
    )
    
    # 1. Position Opened
    open_event = PositionEvent(
        timestamp=timestamp,
        symbol=symbol,
        action="opened",
        volume=Decimal("10"),
        average_price=Decimal("152.0")
    )
    
    observer.on_position_opened(open_event, snapshot)
    
    obs = observer.get_observation(symbol)
    assert obs is not None
    assert obs.symbol == symbol
    assert obs.entry_snapshot.close == Decimal("152")
    assert obs.opened_at == timestamp
    
    # 2. Position Updated
    update_event = PositionEvent(
        timestamp=timestamp,
        symbol=symbol,
        action="updated",
        volume=Decimal("10"),
        average_price=Decimal("152.0")
    )
    observer.on_position_updated(update_event, current_price=150.0)
    
    # 3. Trade Action not closed (coverage for line 62)
    open_trade_event = TradeEvent(
        timestamp=datetime(2023, 1, 1, 12, 30, tzinfo=timezone.utc),
        trade_id="t1",
        symbol=symbol,
        action="opened",
        realized_pnl=Decimal("0.0")
    )
    assert observer.on_trade_closed(open_trade_event) is None
    
    # 4. Trade Closed
    close_event = TradeEvent(
        timestamp=datetime(2023, 1, 1, 13, 0, tzinfo=timezone.utc),
        trade_id="t1",
        symbol=symbol,
        action="closed",
        realized_pnl=Decimal("20.0")
    )
    
    final_obs = observer.on_trade_closed(close_event)
    assert final_obs is not None
    assert final_obs.entry_snapshot.close == Decimal("152")
    
    # Observation should be removed
    assert observer.get_observation(symbol) is None
