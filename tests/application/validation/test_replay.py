import pytest
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from aegis_trade.domain.core import Tick, Symbol, AssetClass
from aegis_trade.application.validation.replay import TickReplayEngine

async def mock_tick_stream(num_ticks: int):
    symbol = Symbol("AAPL", AssetClass.EQUITIES)
    for i in range(num_ticks):
        yield Tick(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            bid=Decimal("150.0") + Decimal(i),
            ask=Decimal("150.1") + Decimal(i)
        )

@pytest.mark.anyio
async def test_tick_replay_engine_processes_all_ticks():
    engine = TickReplayEngine(speed_factor=10000.0) # Very fast so test doesn't hang
    
    received_ticks = []
    
    async def dummy_callback(tick: Tick):
        received_ticks.append(tick)
        
    await engine.run(mock_tick_stream(5), dummy_callback)
    
    assert len(received_ticks) == 5
    assert received_ticks[0].bid == Decimal("150.0")
    assert received_ticks[4].bid == Decimal("154.0")
