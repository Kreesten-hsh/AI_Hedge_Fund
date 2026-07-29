import copy
from typing import Dict, Optional

from aegis_trade.domain.core import Symbol, MarketBar
from aegis_trade.engine.events import MarketEvent


class MarketSnapshotBuilder:
    """
    Maintains the most recent market state (e.g., latest MarketBar per symbol).
    Provides a way to retrieve a cloned snapshot of the current state at any time.
    """
    
    def __init__(self):
        self._latest_bars: Dict[str, MarketBar] = {}
        
    def on_market_event(self, event: MarketEvent) -> None:
        """
        Updates the internal state with the latest market data.
        """
        symbol_str = str(event.bar.symbol)
        self._latest_bars[symbol_str] = event.bar

    def get_snapshot(self, symbol: Symbol) -> Optional[MarketBar]:
        """
        Returns a deep copy of the latest MarketBar for the given symbol,
        or None if no data is available yet.
        """
        symbol_str = str(symbol)
        bar = self._latest_bars.get(symbol_str)
        if bar:
            # We return a clone to ensure the snapshot is immutable/isolated from future updates
            return copy.deepcopy(bar)
        return None
