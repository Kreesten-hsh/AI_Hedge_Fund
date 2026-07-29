from typing import Dict, Optional
from datetime import datetime

from aegis_trade.domain.core import Symbol
from aegis_trade.engine.events import PositionEvent, TradeEvent
from aegis_trade.application.reflection.snapshot import RichMarketSnapshot

class TradeObservation:
    """
    Holds data about a trade currently in progress.
    """
    def __init__(self, symbol: Symbol, entry_snapshot: RichMarketSnapshot, opened_at: datetime):
        self.symbol = symbol
        self.entry_snapshot = entry_snapshot
        self.opened_at = opened_at
        # Here we could also track max_drawdown during the trade lifecycle
        self.max_drawdown_tracked = 0.0


class TradeObserver:
    """
    Observes the lifecycle of trades and stores entry snapshots.
    Listens to PositionEvent to track openings, and cleans up when closed.
    """
    def __init__(self):
        # Maps symbol string to active observation
        self._active_trades: Dict[str, TradeObservation] = {}

    def on_position_opened(self, event: PositionEvent, snapshot: RichMarketSnapshot) -> None:
        """
        Records the start of a trade along with the market snapshot at entry.
        """
        symbol_str = str(event.symbol)
        if event.action == "opened":
            self._active_trades[symbol_str] = TradeObservation(
                symbol=event.symbol,
                entry_snapshot=snapshot,
                opened_at=event.timestamp
            )

    def on_position_updated(self, event: PositionEvent, current_price: float) -> None:
        """
        Updates trade metrics during its lifecycle (e.g., max drawdown).
        """
        symbol_str = str(event.symbol)
        obs = self._active_trades.get(symbol_str)
        if obs and event.action == "updated":
            # Simplified drawdown tracking for now
            # Normally requires side (LONG/SHORT) and peak/trough logic
            # This is a placeholder for real max drawdown calculation
            pass

    def get_observation(self, symbol: Symbol) -> Optional[TradeObservation]:
        return self._active_trades.get(str(symbol))

    def on_trade_closed(self, event: TradeEvent) -> Optional[TradeObservation]:
        """
        Returns the observation for a closed trade and removes it from active tracking.
        """
        symbol_str = str(event.symbol)
        if event.action == "closed":
            return self._active_trades.pop(symbol_str, None)
        return None
