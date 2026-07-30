from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from aegis_trade.domain import Symbol


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    BRACKET = "bracket"
    OCO = "oco"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"


class OrderState(str, Enum):
    CREATED = "created"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ActionType(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class PaperOrder:
    order_id: str
    symbol: Symbol
    action: ActionType
    order_type: OrderType
    volume: Decimal
    timestamp: datetime
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    state: OrderState = OrderState.CREATED
    filled_volume: Decimal = Decimal("0.0")
    average_fill_price: Decimal = Decimal("0.0")
    context_features: dict = field(default_factory=dict)
    
    def can_transition_to(self, new_state: OrderState) -> bool:
        valid_transitions = {
            OrderState.CREATED: [OrderState.SUBMITTED, OrderState.REJECTED],
            OrderState.SUBMITTED: [OrderState.ACCEPTED, OrderState.REJECTED, OrderState.CANCELLED],
            OrderState.ACCEPTED: [OrderState.PARTIALLY_FILLED, OrderState.FILLED, OrderState.CANCELLED, OrderState.EXPIRED],
            OrderState.PARTIALLY_FILLED: [OrderState.FILLED, OrderState.CANCELLED, OrderState.EXPIRED, OrderState.PARTIALLY_FILLED],
            OrderState.FILLED: [],
            OrderState.CANCELLED: [],
            OrderState.REJECTED: [],
            OrderState.EXPIRED: []
        }
        return new_state in valid_transitions[self.state]


@dataclass(frozen=True)
class PaperFill:
    fill_id: str
    order_id: str
    symbol: Symbol
    action: ActionType
    volume: Decimal
    price: Decimal
    commission: Decimal
    timestamp: datetime
    context_features: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PaperExecution:
    execution_id: str
    order_id: str
    timestamp: datetime
    requested_price: Decimal
    execution_price: Decimal
    slippage: Decimal
    latency_ms: float


@dataclass(frozen=True)
class PaperPosition:
    symbol: Symbol
    volume: Decimal
    average_price: Decimal
    unrealized_pnl: Decimal = Decimal("0.0")
    realized_pnl: Decimal = Decimal("0.0")


@dataclass(frozen=True)
class PaperBalance:
    currency: str
    total: Decimal
    locked: Decimal
    available: Decimal


@dataclass(frozen=True)
class PaperAccount:
    account_id: str
    balances: dict[str, PaperBalance] = field(default_factory=dict)
    positions: dict[Symbol, PaperPosition] = field(default_factory=dict)


@dataclass(frozen=True)
class PaperTrade:
    trade_id: str
    entry_fill: PaperFill
    exit_fill: Optional[PaperFill] = None
    realized_pnl: Optional[Decimal] = None
    is_open: bool = True


@dataclass(frozen=True)
class PaperExecutionReport:
    timestamp: datetime
    order: PaperOrder
    risk_decision: str
    execution: Optional[PaperExecution] = None
    fills: List[PaperFill] = field(default_factory=list)
    portfolio_value_before: Optional[Decimal] = None
    portfolio_value_after: Optional[Decimal] = None


@dataclass(frozen=True)
class PaperSession:
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    is_active: bool = True


@dataclass(frozen=True)
class PaperPortfolioSnapshot:
    timestamp: datetime
    balance: Decimal
    equity: Decimal
    drawdown: float
    gross_exposure: Decimal
    net_exposure: Decimal
    open_positions_count: int
    margin_used: Decimal
    daily_pnl: Decimal
    floating_pnl: Decimal
