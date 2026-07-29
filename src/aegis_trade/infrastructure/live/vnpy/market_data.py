from typing import Callable, Awaitable
from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.domain.core import Symbol, MarketBar, TimeFrame
from aegis_trade.engine.events import MarketEvent

class VnPyMarketGateway:
    def __init__(self, event_publisher: Callable[[any], Awaitable[None]], symbol_mapper):
        self.event_publisher = event_publisher
        self.symbol_mapper = symbol_mapper

    async def on_tick(self, tick):
        """
        Callback for vn.py tick data.
        Translates EVENT_TICK to Aegis MarketEvent.
        """
        symbol = self.symbol_mapper.from_vnpy_symbol(tick.vt_symbol)
        
        # In a real scenario, map tick data to MarketBar
        # For LIVE-02 MVP we extract the last price
        bar = MarketBar(
            symbol=symbol,
            timeframe=TimeFrame.M1,
            timestamp=datetime.now(timezone.utc), # Use tick.datetime if available and tz-aware
            open=Decimal(str(tick.last_price)),
            high=Decimal(str(tick.last_price)),
            low=Decimal(str(tick.last_price)),
            close=Decimal(str(tick.last_price)),
            volume=Decimal(str(tick.volume))
        )
        
        event = MarketEvent(bar=bar, timestamp=bar.timestamp)
        await self.event_publisher(event)
