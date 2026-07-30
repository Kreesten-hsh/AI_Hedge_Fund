import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone

from aegis_trade.application.monitoring.engine import MonitoringEngine
from aegis_trade.engine.events import PositionEvent, EngineEventType
from aegis_trade.domain import Symbol

@pytest.mark.asyncio
async def test_trade_record_computes_real_pnl_not_zero():
    engine = MonitoringEngine()
    
    # 1. Open a position
    symbol = Symbol(name="EURUSD", asset_class="forex")
    
    open_event = PositionEvent(
        symbol=symbol,
        action="opened",
        volume=Decimal("1000.0"),
        average_price=Decimal("1.1000"),
        timestamp=datetime.now(timezone.utc)
    )
    
    await engine.process_event(open_event)
    
    # Verify position is recorded
    assert "EURUSD" in engine.positions
    pos = engine.positions["EURUSD"]
    assert pos.quantity == Decimal("1000.0")
    assert pos.entry_price == Decimal("1.1000")
    
    # 2. Close the position with a profit
    close_event = PositionEvent(
        symbol=symbol,
        action="closed",
        volume=Decimal("0.0"),
        average_price=Decimal("1.1100"), # 100 pips profit
        timestamp=datetime.now(timezone.utc)
    )
    
    await engine.process_event(close_event)
    
    # Verify trade was created
    trades = engine.get_trades()
    assert len(trades) == 1
    
    trade = trades[0]
    
    # Since it's LONG, (1.1100 - 1.1000) * 1000 * 1 = 10.0
    assert trade.realized_pnl_amount == Decimal("10.0000")
    assert trade.realized_pnl_percent > Decimal("0.9")
    assert trade.realized_pnl_percent < Decimal("1.0")
