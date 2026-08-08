from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from aegis_trade.domain import MarketBar, Symbol, ExitReason

class EngineEventType(str, Enum):
    MARKET = "market"
    SIGNAL = "signal"
    ORDER = "order"
    FILL = "fill"
    PORTFOLIO = "portfolio"
    METRICS = "metrics"
    AUDIT = "audit"
    ORDER_LIFECYCLE = "order_lifecycle"
    POSITION = "position"
    ACCOUNT = "account"
    TRADE = "trade"
    MEMORY = "memory"

class SignalIntent(str, Enum):
    ENTER_LONG = "enter_long"
    ENTER_SHORT = "enter_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    HOLD = "hold"

class OrderAction(str, Enum):
    BUY = "buy"
    SELL = "sell"

@dataclass(frozen=True)
class EngineEvent:
    """Base class for all events in the Trading Engine."""
    event_type: EngineEventType = field(init=False)
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("EngineEvent timestamps must be timezone-aware.")
        if self.timestamp.tzinfo != timezone.utc:
            raise ValueError("EngineEvent timestamps must be strictly in UTC.")

@dataclass(frozen=True)
class MarketEvent(EngineEvent):
    """Event triggered when a new market bar/tick is received."""
    bar: MarketBar
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.MARKET)
        object.__setattr__(self, 'timestamp', self.bar.timestamp)
        super().__post_init__()

@dataclass(frozen=True)
class SignalEvent(EngineEvent):
    """Event triggered by a Strategy indicating an intent to trade."""
    symbol: Symbol
    intent: SignalIntent
    strategy_id: str
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.SIGNAL)
        super().__post_init__()

@dataclass(frozen=True)
class OrderEvent(EngineEvent):
    """Event triggered by the Risk Engine indicating an approved order to execute."""
    symbol: Symbol
    action: OrderAction
    volume: Decimal
    order_type: str = "market" # market, limit, stop, etc.
    strategy_id: str = "unknown"
    context_features: dict = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.ORDER)
        if self.volume <= 0:
            raise ValueError("Order volume must be strictly positive.")
        super().__post_init__()

@dataclass(frozen=True)
class FillEvent(EngineEvent):
    """Event triggered by the Broker when an order is executed."""
    symbol: Symbol
    action: OrderAction
    volume: Decimal
    fill_price: Decimal
    commission: Decimal
    exchange: str
    strategy_id: str
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.FILL)
        if self.volume <= 0:
            raise ValueError("Fill volume must be strictly positive.")
        if self.fill_price <= 0:
            raise ValueError("Fill price must be strictly positive.")
        if self.commission < 0:
            raise ValueError("Commission cannot be negative.")
        super().__post_init__()

@dataclass(frozen=True)
class AuditEvent(EngineEvent):
    """Event triggered to log audit traces, such as risk rejections."""
    audit_type: str
    message: str
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.AUDIT)
        super().__post_init__()

# --- Extended Lifecycle Events (e.g. for Paper/Live Trading) ---

@dataclass(frozen=True)
class OrderLifecycleEvent(EngineEvent):
    order_id: str
    status: str # submitted, accepted, filled, cancelled, rejected, expired
    message: str = ""
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.ORDER_LIFECYCLE)
        super().__post_init__()

@dataclass(frozen=True)
class PositionEvent(EngineEvent):
    symbol: Symbol
    action: str # opened, closed, updated
    volume: Decimal
    average_price: Decimal
    context_features: dict = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.POSITION)
        super().__post_init__()

@dataclass(frozen=True)
class AccountEvent(EngineEvent):
    account_id: str
    action: str # balance_updated, margin_changed
    currency: str
    amount: Decimal
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.ACCOUNT)
        super().__post_init__()

@dataclass(frozen=True)
class MetricsEvent(EngineEvent):
    """Snapshot périodique du portefeuille (equity, drawdown, expositions).

    `EngineEventType.METRICS` existait sans porteur : la boucle de monitoring
    calculait un snapshot puis le jetait faute d'événement pour le transporter.
    """
    metrics: dict[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.METRICS)
        super().__post_init__()

@dataclass(frozen=True)
class TradeEvent(EngineEvent):
    trade_id: str
    symbol: Symbol
    action: str # opened, updated, closed
    realized_pnl: Decimal
    exit_reason: ExitReason | None = None
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.TRADE)
        super().__post_init__()

# --- Memory / Reflection Events ---

@dataclass(frozen=True)
class ExperienceSavedEvent(EngineEvent):
    experience_id: str
    category: str
    pnl: Decimal
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.MEMORY)
        super().__post_init__()

@dataclass(frozen=True)
class ExperienceRejectedEvent(EngineEvent):
    reason: str
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.MEMORY)
        super().__post_init__()

@dataclass(frozen=True)
class DuplicateExperienceEvent(EngineEvent):
    experience_id: str
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.MEMORY)
        super().__post_init__()

@dataclass(frozen=True)
class MemoryOverflowEvent(EngineEvent):
    message: str
    
    def __post_init__(self) -> None:
        object.__setattr__(self, 'event_type', EngineEventType.MEMORY)
        super().__post_init__()
