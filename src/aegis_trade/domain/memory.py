from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Mapping, Sequence

from aegis_trade.domain.core import Symbol, TimeFrame, Side


class MemoryCategory(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    NEAR_MISS = "near_miss"
    EXCEPTIONAL = "exceptional"
    UNKNOWN = "unknown"


class MarketSession(str, Enum):
    LONDON = "london"
    NEW_YORK = "new_york"
    TOKYO = "tokyo"
    ASIAN_BOX = "asian_box"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class MarketFeatures:
    """Represents the raw/extracted features of the market before vectorization."""
    # Market Data
    price: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    spread: float
    volume: float
    order_book_imbalance: float
    
    # Time & Session
    time_of_day: float  # usually fractional hour or minute of day
    session: MarketSession
    time_since_economic_event_min: float
    economic_calendar_flag: bool
    
    # Oscillators & Trend
    ema_distance: float
    rsi: float
    macd: float
    momentum_roc: float
    vwap_distance: float
    
    # Volatility & Liquidity
    atr: float
    volatility_state: float
    liquidity_density: float
    
    # Portfolio Correlation
    portfolio_correlation: float


@dataclass(frozen=True, slots=True)
class Experience:
    """Represents a complete context of a trade and its result."""
    id: str
    timestamp: datetime
    symbol: Symbol
    timeframe: TimeFrame
    features: MarketFeatures
    decision_side: Side
    
    # Result Metrics
    pnl: Decimal
    max_drawdown: Decimal
    duration_seconds: int
    
    # Processed Data
    category: MemoryCategory
    embedding: tuple[float, ...]
    
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Experience ID cannot be empty.")
        if self.timestamp.tzinfo != timezone.utc:
            raise ValueError("Experience timestamp must be UTC.")
        if self.duration_seconds < 0:
            raise ValueError("Experience duration cannot be negative.")
        if not self.embedding:
            raise ValueError("Experience embedding cannot be empty.")


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Represents a found experience from the vector store."""
    experience: Experience
    distance: float
    similarity_score: float

    def __post_init__(self) -> None:
        if self.similarity_score < -100 or self.similarity_score > 100:
            raise ValueError("Similarity score must be between -100 and +100.")

