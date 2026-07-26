from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from aegis_trade.domain.core import Symbol, TimeFrame

@dataclass(frozen=True, slots=True)
class DataContext:
    """
    Metadata associated with a data ingestion operation.
    """
    provider: str
    symbol: Symbol
    timeframe: Optional[TimeFrame]
    timezone: str
    source: str
    retrieved_at: datetime
    latency: float
    cache_hit: bool

    def __post_init__(self) -> None:
        if self.retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at timestamp must be timezone-aware.")
        if self.latency < 0:
            raise ValueError("Latency cannot be negative.")
