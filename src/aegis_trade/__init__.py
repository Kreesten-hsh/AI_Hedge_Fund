"""
Aegis Quant OS - Root API

A local-first foundation for research, backtesting, and MT5 demo trading.
"""

from .domain import (
    Side,
    AssetClass,
    Symbol,
    TimeFrame,
    MarketBar,
    Tick,
    Position,
    Trade,
    Signal,
    TradeProposal,
    DataColumn,
    DatasetLineage,
    InstrumentSpec,
    AccountSnapshot,
    RiskDecision,
    ExecutionReport,
    BacktestEntry,
    BacktestResult,
    AuditEvent,
    HealthStatus
)

from aegis_trade.core.exceptions import (
    AegisError,
    DataError,
    DataFetchError,
    MissingData,
    CorruptedData,
    InvalidMarketBar,
    InvalidTick,
    MarketClosed,
    AuthenticationError,
    RateLimitError,
    ProviderUnavailable
)

__all__ = [
    # Domain
    "Side",
    "AssetClass",
    "Symbol",
    "TimeFrame",
    "MarketBar",
    "Tick",
    "Position",
    "Trade",
    "Signal",
    "TradeProposal",
    "DataColumn",
    "DatasetLineage",
    "InstrumentSpec",
    "AccountSnapshot",
    "RiskDecision",
    "ExecutionReport",
    "BacktestEntry",
    "BacktestResult",
    "AuditEvent",
    "HealthStatus",
    
    # Exceptions
    "AegisError",
    "DataError",
    "DataFetchError",
    "MissingData",
    "CorruptedData",
    "InvalidMarketBar",
    "InvalidTick",
    "MarketClosed",
    "AuthenticationError",
    "RateLimitError",
    "ProviderUnavailable"
]
