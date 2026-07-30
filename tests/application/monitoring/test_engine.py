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

@pytest.mark.asyncio
async def test_reflection_pipeline_uses_real_market_context_not_random_values():
    from unittest.mock import MagicMock
    engine = MonitoringEngine()
    engine.knowledge_repo = MagicMock()
    engine.knowledge_generator = MagicMock()
    engine.cluster_engine = MagicMock()
    
    symbol1 = Symbol(name="BTCUSD", asset_class="crypto")
    symbol2 = Symbol(name="ETHUSD", asset_class="crypto")
    
    # Trade 1 with specific context
    open1 = PositionEvent(
        symbol=symbol1, action="opened", volume=Decimal("1.0"), average_price=Decimal("50000"),
        timestamp=datetime.now(timezone.utc),
        context_features={"rsi": 30.5, "ema_distance": -0.2, "atr": 500.0}
    )
    await engine.process_event(open1)
    
    close1 = PositionEvent(
        symbol=symbol1, action="closed", volume=Decimal("0.0"), average_price=Decimal("51000"),
        timestamp=datetime.now(timezone.utc)
    )
    await engine.process_event(close1)
    
    # Trade 2 with different context
    open2 = PositionEvent(
        symbol=symbol2, action="opened", volume=Decimal("10.0"), average_price=Decimal("3000"),
        timestamp=datetime.now(timezone.utc),
        context_features={"rsi": 80.0, "ema_distance": 0.5, "atr": 100.0}
    )
    await engine.process_event(open2)
    
    close2 = PositionEvent(
        symbol=symbol2, action="closed", volume=Decimal("0.0"), average_price=Decimal("2900"),
        timestamp=datetime.now(timezone.utc)
    )
    await engine.process_event(close2)
    
    # Wait for async tasks (reflection pipeline)
    await asyncio.sleep(0.1)
    
    assert len(engine.experience_buffer) == 2
    
    exp1 = engine.experience_buffer[0]
    exp2 = engine.experience_buffer[1]
    
    # Verify embedding strictly matches the context_features passed at open
    # embedding order in code: (rsi, ema_distance, atr)
    assert exp1.embedding == (30.5, -0.2, 500.0)
    assert exp2.embedding == (80.0, 0.5, 100.0)
    
    # It must be deterministic, not random
    assert exp1.embedding != exp2.embedding
