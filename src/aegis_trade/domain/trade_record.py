from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from aegis_trade.domain.core import Symbol

class TradeMode(Enum):
    DEMO = "DEMO"
    PAPER = "PAPER"
    LIVE = "LIVE"

@dataclass
class TradeRecord:
    """
    Represents a fully executed round-trip trade.
    Persisted for historical performance tracking on the dashboard.
    """
    trade_id: str
    symbol: Symbol
    side: str  # "LONG" or "SHORT"
    entry_price: Decimal
    exit_price: Decimal
    volume: Decimal
    realized_pnl_amount: Decimal
    realized_pnl_percent: Decimal
    open_timestamp: datetime
    close_timestamp: datetime
    duration_seconds: float
    spread: Decimal = Decimal(0)
    triggering_council_verdict_id: Optional[str] = None
    mode: TradeMode = TradeMode.PAPER
