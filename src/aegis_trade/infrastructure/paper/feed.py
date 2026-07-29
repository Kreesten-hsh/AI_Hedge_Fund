import asyncio
from typing import AsyncGenerator, List
from aegis_trade.application.paper_trading.interfaces import IMarketFeed
from aegis_trade.domain import MarketBar


class MarketReplayFeed(IMarketFeed):
    """
    A simple feed that replays a predefined list of market bars.
    Can be configured to yield bar by bar without delay, or simulate real-time ticks.
    """
    def __init__(self, historical_data: List[MarketBar], delay_ms: float = 0.0):
        self.historical_data = historical_data
        self.delay_ms = delay_ms

    async def subscribe(self) -> AsyncGenerator[MarketBar, None]:
        for bar in self.historical_data:
            if self.delay_ms > 0:
                await asyncio.sleep(self.delay_ms / 1000.0)
            yield bar
