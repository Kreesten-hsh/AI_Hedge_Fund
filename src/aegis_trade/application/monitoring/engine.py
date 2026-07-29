import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Callable, Awaitable
from pydantic import BaseModel

from aegis_trade.engine.events import (
    EngineEvent, EngineEventType, OrderLifecycleEvent, PositionEvent, AccountEvent, TradeEvent
)
from aegis_trade.application.monitoring.models import (
    PortfolioSnapshot, PositionSnapshot, RiskSnapshot, SystemSnapshot,
    PerformanceSnapshot, PaperTradingSnapshot
)

class MonitoringEngine:
    def __init__(self):
        # Latest snapshots
        self.portfolio: PortfolioSnapshot | None = None
        self.risk: RiskSnapshot | None = None
        self.system: SystemSnapshot | None = None
        self.performance: PerformanceSnapshot | None = None
        self.paper_trading: PaperTradingSnapshot | None = None
        
        # State
        self.positions: Dict[str, PositionSnapshot] = {}
        
        # Historical Data (In-Memory for now, could be backed by SQLite later)
        self.history_1m: List[PortfolioSnapshot] = []
        self.history_5m: List[PortfolioSnapshot] = []
        self.history_1h: List[PortfolioSnapshot] = []
        self.history_1d: List[PortfolioSnapshot] = []
        
        # Callbacks for WebSocket broadcasting
        self.on_snapshot_updated: List[Callable[[str, BaseModel], Awaitable[None]]] = []
        
        self._initialize_empty_snapshots()
        
    def _initialize_empty_snapshots(self):
        now = datetime.now(timezone.utc)
        self.portfolio = PortfolioSnapshot(
            timestamp=now, equity=Decimal(0), cash=Decimal(0),
            total_unrealized_pnl=Decimal(0), total_realized_pnl=Decimal(0), open_positions_count=0
        )
        self.risk = RiskSnapshot(
            timestamp=now, global_exposure=Decimal(0), distance_to_max_drawdown=Decimal(0),
            risk_status="NORMAL"
        )
        self.system = SystemSnapshot(
            timestamp=now, cpu_usage=0.0, memory_usage=0.0, disk_usage=0.0, active_services=[]
        )

    def register_callback(self, callback: Callable[[str, BaseModel], Awaitable[None]]):
        self.on_snapshot_updated.append(callback)

    async def _broadcast(self, topic: str, snapshot: BaseModel):
        for cb in self.on_snapshot_updated:
            try:
                await cb(topic, snapshot)
            except Exception as e:
                # Log error
                pass

    async def process_event(self, event: EngineEvent):
        """Main entrypoint for the EventBus to feed the monitoring engine."""
        now = datetime.now(timezone.utc)
        updated_topics = []

        if event.event_type == EngineEventType.ACCOUNT:
            ev: AccountEvent = event
            if ev.action == "balance_updated":
                self.portfolio.cash = ev.amount
                self.portfolio.equity = self.portfolio.cash + self.portfolio.total_unrealized_pnl
                self.portfolio.timestamp = now
                updated_topics.append(("portfolio", self.portfolio))

        elif event.event_type == EngineEventType.POSITION:
            ev: PositionEvent = event
            symbol_name = ev.symbol.name
            
            if ev.action == "opened" or ev.action == "updated":
                self.positions[symbol_name] = PositionSnapshot(
                    symbol=symbol_name,
                    side="LONG" if ev.volume > 0 else "SHORT",
                    quantity=ev.volume,
                    entry_price=ev.average_price,
                    current_price=ev.average_price,
                    unrealized_pnl=Decimal(0)
                )
            elif ev.action == "closed":
                if symbol_name in self.positions:
                    del self.positions[symbol_name]
            
            self.portfolio.open_positions_count = len(self.positions)
            self.portfolio.timestamp = now
            updated_topics.append(("positions", self.portfolio)) # we could broadcast just the diff

        elif event.event_type == EngineEventType.ORDER_LIFECYCLE:
            pass # Handle order events if needed for specific snapshots

        for topic, snapshot in updated_topics:
            await self._broadcast(topic, snapshot)

    def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        return self.portfolio
