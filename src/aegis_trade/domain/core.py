from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Mapping, Sequence, Literal, NamedTuple


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"

class AssetClass(str, Enum):
    FOREX = "forex"
    CRYPTO = "crypto"
    EQUITIES = "equities"
    COMMODITIES = "commodities"
    INDICES = "indices"
    FUTURES = "futures"
    OPTIONS = "options"

@dataclass(frozen=True, slots=True)
class Symbol:
    name: str
    asset_class: AssetClass

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Symbol name cannot be empty.")

class TimeFrame(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"

@dataclass(frozen=True, slots=True)
class MarketBar:
    symbol: Symbol
    timeframe: TimeFrame
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo != timezone.utc:
            raise ValueError("MarketBar timestamp must be UTC.")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("MarketBar prices must be positive.")
        if self.high < max(self.open, self.close):
            raise ValueError("MarketBar high cannot be below open or close.")
        if self.low > min(self.open, self.close):
            raise ValueError("MarketBar low cannot be above open or close.")
        if self.volume < 0:
            raise ValueError("MarketBar volume cannot be negative.")

@dataclass(frozen=True, slots=True)
class EconomicIndicator:
    symbol: Symbol
    timestamp: datetime
    value: Decimal
    forecast: Decimal | None = None
    previous: Decimal | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo != timezone.utc:
            raise ValueError("EconomicIndicator timestamp must be UTC.")


@dataclass(frozen=True, slots=True)
class NewsItem:
    symbol: Symbol
    timestamp: datetime
    title: str
    source: str
    sentiment_score: float | None = None
    url: str | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo != timezone.utc:
            raise ValueError("NewsItem timestamp must be UTC.")
        if not self.title:
            raise ValueError("NewsItem must have a title.")


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    symbol: Symbol
    timestamp: datetime
    price: Decimal
    volume: Decimal | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo != timezone.utc:
            raise ValueError("MarketSnapshot timestamp must be UTC.")
        if self.price <= 0:
            raise ValueError("MarketSnapshot price must be positive.")


@dataclass(frozen=True, slots=True)
class Tick:
    symbol: Symbol
    timestamp: datetime
    bid: Decimal
    ask: Decimal

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo != timezone.utc:
            raise ValueError("Tick timestamp must be UTC.")
        if min(self.bid, self.ask) <= 0:
            raise ValueError("Tick prices must be positive.")
        if self.bid > self.ask:
            raise ValueError("Tick bid cannot be greater than ask.")

@dataclass(frozen=True, slots=True)
class Position:
    symbol: Symbol
    side: Side
    entry_price: Decimal
    volume: Decimal
    opened_at: datetime

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo != timezone.utc:
            raise ValueError("Position opened_at must be UTC.")
        if self.entry_price <= 0:
            raise ValueError("Position entry_price must be positive.")
        if self.volume <= 0:
            raise ValueError("Position volume must be strictly positive.")

@dataclass(frozen=True, slots=True)
class Trade:
    position: Position
    exit_price: Decimal
    closed_at: datetime

    def __post_init__(self) -> None:
        if self.closed_at.tzinfo != timezone.utc:
            raise ValueError("Trade closed_at must be UTC.")
        if self.exit_price <= 0:
            raise ValueError("Trade exit_price must be positive.")
        if self.closed_at <= self.position.opened_at:
            raise ValueError("Trade closed_at must be after position opened_at.")


@dataclass(frozen=True, slots=True)
class Signal:
    symbol: Symbol
    side: Side
    observed_at: datetime
    strategy_id: str

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValueError("Signal timestamps must be timezone-aware.")
        if not self.strategy_id:
            raise ValueError("A signal requires a strategy identifier.")


@dataclass(frozen=True, slots=True)
class TradeProposal:
    symbol: Symbol
    side: Side
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    strategy_id: str

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("A trade proposal requires a strategy identifier.")
        if min(self.entry_price, self.stop_loss, self.take_profit) <= 0:
            raise ValueError("Trade prices must be positive.")
        if self.side is Side.LONG and not self.stop_loss < self.entry_price < self.take_profit:
            raise ValueError("Long proposals require stop < entry < target.")
        if self.side is Side.SHORT and not self.take_profit < self.entry_price < self.stop_loss:
            raise ValueError("Short proposals require target < entry < stop.")


# Global Universal Column Abstraction
@dataclass(frozen=True)
class DataColumn:
    name: str
    values: Sequence[float | int | None]
    
@dataclass(frozen=True)
class DatasetLineage:
    parent_hash: str
    parent_type: str
    pipeline_version: str


@dataclass(frozen=True, slots=True)
class InstrumentSpec:
    symbol: Symbol
    contract_size: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal

    def __post_init__(self) -> None:
        if min(self.contract_size, self.minimum_volume, self.maximum_volume, self.volume_step) <= 0:
            raise ValueError("Instrument quantities must be positive.")
        if self.minimum_volume > self.maximum_volume:
            raise ValueError("Minimum volume cannot exceed maximum volume.")


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    equity: Decimal
    daily_realized_loss: Decimal
    weekly_realized_loss: Decimal
    gross_exposure: Decimal
    correlated_positions: int

    def __post_init__(self) -> None:
        if self.equity <= 0:
            raise ValueError("Account equity must be positive.")
        if min(self.daily_realized_loss, self.weekly_realized_loss, self.gross_exposure) < 0:
            raise ValueError("Account loss and exposure values cannot be negative.")
        if self.correlated_positions < 0:
            raise ValueError("Correlated position count cannot be negative.")


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    volume: Decimal
    risk_amount: Decimal
    rejection_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    order_id: str
    accepted: bool
    environment: str
    fill_price: Decimal | None
    volume: Decimal
    message: str


@dataclass(frozen=True, slots=True)
class BacktestEntry:
    symbol: Symbol
    side: Side
    signal_observed_at: datetime
    filled_at: datetime
    fill_price: Decimal

    def __post_init__(self) -> None:
        if self.signal_observed_at.tzinfo is None or self.filled_at.tzinfo is None:
            raise ValueError("Backtest timestamps must be timezone-aware.")
        if self.filled_at <= self.signal_observed_at:
            raise ValueError("Backtest fills must follow the observed signal.")
        if self.fill_price <= 0:
            raise ValueError("Backtest fill prices must be positive.")


@dataclass(frozen=True, slots=True)
class BacktestResult:
    entries: tuple[BacktestEntry, ...]


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_type: str
    occurred_at: datetime
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ValueError("An audit event requires an event type.")
        if self.occurred_at.tzinfo is None:
            raise ValueError("Audit timestamps must be timezone-aware.")


@dataclass(frozen=True, slots=True)
class HealthStatus:
    connected: bool
    latency: float
    provider: str
    version: str
    last_error: str | None
