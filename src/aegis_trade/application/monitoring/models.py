from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

class PortfolioSnapshot(BaseModel):
    timestamp: datetime
    equity: Decimal
    cash: Decimal
    total_unrealized_pnl: Decimal
    total_realized_pnl: Decimal
    open_positions_count: int

class PositionSnapshot(BaseModel):
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal

class RiskSnapshot(BaseModel):
    timestamp: datetime
    global_exposure: Decimal
    distance_to_max_drawdown: Decimal
    risk_status: str # NORMAL, WARNING, CRITICAL, HALTED

class SystemSnapshot(BaseModel):
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_services: List[str]

class PerformanceSnapshot(BaseModel):
    timestamp: datetime
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    expectancy: float

class PaperTradingSnapshot(BaseModel):
    timestamp: datetime
    total_orders_executed: int
    average_slippage: float
    average_latency_ms: float
