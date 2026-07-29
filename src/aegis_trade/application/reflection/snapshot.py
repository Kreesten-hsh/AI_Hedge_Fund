import copy
from typing import Dict, Optional, Deque
from collections import deque
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

from aegis_trade.domain.core import Symbol, MarketBar
from aegis_trade.engine.events import MarketEvent

@dataclass(frozen=True)
class RichMarketSnapshot:
    symbol: Symbol
    timestamp: datetime
    latest_bar: MarketBar
    history: pd.DataFrame


class MarketSnapshotBuilder:
    """
    Maintains a rolling window of recent MarketBars.
    Provides a way to retrieve a RichMarketSnapshot.
    """
    
    def __init__(self, window_size: int = 100):
        self._window_size = window_size
        self._history: Dict[str, Deque[MarketBar]] = {}
        
    def on_market_event(self, event: MarketEvent) -> None:
        """
        Updates the internal state with the latest market data.
        """
        symbol_str = str(event.bar.symbol)
        if symbol_str not in self._history:
            self._history[symbol_str] = deque(maxlen=self._window_size)
        self._history[symbol_str].append(event.bar)

    def get_snapshot(self, symbol: Symbol) -> Optional[RichMarketSnapshot]:
        """
        Returns a deep copy of the latest state in a RichMarketSnapshot.
        """
        symbol_str = str(symbol)
        bars = self._history.get(symbol_str)
        if not bars:
            return None
            
        df = pd.DataFrame([
            {
                'timestamp': b.timestamp,
                'open': float(b.open),
                'high': float(b.high),
                'low': float(b.low),
                'close': float(b.close),
                'volume': float(b.volume)
            }
            for b in bars
        ])
        
        latest = copy.deepcopy(bars[-1])
        return RichMarketSnapshot(
            symbol=symbol,
            timestamp=latest.timestamp,
            latest_bar=latest,
            history=df
        )
