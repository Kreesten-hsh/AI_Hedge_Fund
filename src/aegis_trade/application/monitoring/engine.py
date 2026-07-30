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
    PerformanceSnapshot, PaperTradingSnapshot, BrokerSnapshot, StrategySnapshot
)
from aegis_trade.domain.trade_record import TradeRecord, TradeMode
from aegis_trade.domain.memory import Experience, MarketFeatures, MemoryCategory, MarketSession
import uuid
import os
import random

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
        self.trades: List[TradeRecord] = []
        
        # Historical Data (In-Memory for now, could be backed by SQLite later)
        self.history_1m: List[PortfolioSnapshot] = []
        self.history_5m: List[PortfolioSnapshot] = []
        self.history_1h: List[PortfolioSnapshot] = []
        self.history_1d: List[PortfolioSnapshot] = []
        
        # Reasoning references injected via deps
        self.knowledge_repo = None
        self.knowledge_generator = None
        self.cluster_engine = None
        self.experience_buffer: List[Experience] = []
        
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
            timestamp=now, 
            current_mode="LIVE" if os.environ.get("AEGIS_ENV", "").upper() == "LIVE" else "PAPER",
            cpu_usage=0.0, 
            memory_usage=0.0, 
            disk_usage=0.0, 
            active_services=["api", "ws"],
            broker_status=BrokerSnapshot(
                connected=True,
                latency_ms=12.5,
                gateway="BINANCE",
                last_heartbeat=now
            ),
            strategy_status=StrategySnapshot(
                id="alpha_momentum_v1",
                status="Live",
                running_time="14h 22m"
            )
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
                existing = self.positions.get(symbol_name)
                open_ts = existing.open_timestamp if existing else now
                self.positions[symbol_name] = PositionSnapshot(
                    symbol=symbol_name,
                    side="LONG" if ev.volume > 0 else "SHORT",
                    quantity=ev.volume,
                    entry_price=ev.average_price,
                    current_price=ev.average_price,
                    unrealized_pnl=Decimal(0),
                    open_timestamp=open_ts,
                    opening_context=getattr(ev, "context_features", {})
                )
            elif ev.action == "closed":
                if symbol_name in self.positions:
                    pos = self.positions[symbol_name]
                    # Calculate real PnL
                    multiplier = Decimal(1) if pos.side == "LONG" else Decimal(-1)
                    realized_pnl_amount = (ev.average_price - pos.entry_price) * pos.quantity * multiplier
                    
                    if pos.entry_price > 0 and pos.quantity > 0:
                        realized_pnl_percent = (realized_pnl_amount / (pos.entry_price * pos.quantity)) * Decimal(100)
                    else:
                        realized_pnl_percent = Decimal(0)
                        
                    duration = (now - pos.open_timestamp).total_seconds()
                    
                    # Create a TradeRecord based on the position that just closed
                    trade = TradeRecord(
                        trade_id=f"TRD-{uuid.uuid4().hex[:8]}",
                        symbol=ev.symbol,
                        side=pos.side,
                        entry_price=pos.entry_price,
                        exit_price=ev.average_price,
                        volume=pos.quantity,
                        realized_pnl_amount=realized_pnl_amount,
                        realized_pnl_percent=realized_pnl_percent,
                        open_timestamp=pos.open_timestamp,
                        close_timestamp=now,
                        duration_seconds=duration
                    )
                    self.trades.append(trade)
                    del self.positions[symbol_name]
                    updated_topics.append(("trades", trade)) # Broadcast new trade
                    
                    # AI-03: Trigger reflection asynchronously
                    asyncio.create_task(self._run_reflection_pipeline(trade, pos))

            
            self.portfolio.open_positions_count = len(self.positions)
            self.portfolio.timestamp = now
            updated_topics.append(("positions", self.portfolio)) # we could broadcast just the diff

        elif event.event_type == EngineEventType.ORDER_LIFECYCLE:
            pass # Handle order events if needed for specific snapshots

        for topic, snapshot in updated_topics:
            await self._broadcast(topic, snapshot)

    def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        return self.portfolio

    def get_trades(self) -> List[TradeRecord]:
        return self.trades

    async def _run_reflection_pipeline(self, trade: TradeRecord, pos: PositionSnapshot):
        if not self.knowledge_repo or not self.cluster_engine or not self.knowledge_generator:
            return
            
        # Create a basic Experience object from the trade
        cat = MemoryCategory.SUCCESS if trade.realized_pnl_percent > 0 else MemoryCategory.FAILURE
        
        # Use stored real features or fallbacks if none exist
        context = pos.opening_context or {}
        real_rsi = context.get("rsi", 50.0)
        real_ema_distance = context.get("ema_distance", 0.0)
        real_atr = context.get("atr", 0.1)

        features = MarketFeatures(
            price=float(trade.entry_price), open_price=float(trade.entry_price),
            high_price=float(trade.entry_price), low_price=float(trade.entry_price),
            close_price=float(trade.entry_price), spread=0.01, volume=100.0,
            order_book_imbalance=0.0, time_of_day=10.0, session=MarketSession.NEW_YORK,
            time_since_economic_event_min=60.0, economic_calendar_flag=False,
            ema_distance=real_ema_distance, rsi=real_rsi, 
            macd=0.0, momentum_roc=0.0, vwap_distance=0.0, atr=real_atr, volatility_state=0.0, 
            liquidity_density=0.0, portfolio_correlation=0.0
        )
        
        exp = Experience(
            id=f"EXP-{uuid.uuid4().hex[:8]}",
            timestamp=trade.close_timestamp,
            symbol=trade.symbol,
            timeframe="1m",  # Or get from trade if we have it
            features=features,
            decision_side=trade.side,
            pnl=trade.realized_pnl_amount,
            max_drawdown=Decimal(0),
            duration_seconds=int(trade.duration_seconds),
            category=cat,
            embedding=(float(features.rsi), float(features.ema_distance), float(features.atr))
        )
        
        self.experience_buffer.append(exp)
        
        # Run clustering if we have enough recent experiences
        if len(self.experience_buffer) >= 5:
            vectors = [list(e.embedding) for e in self.experience_buffer]
            metadata = [{"id": e.id, "category": e.category} for e in self.experience_buffer]
            
            # Use basic clustering logic from HDBSCAN/DBSCAN in the engine
            clusters = self.cluster_engine.find_clusters(vectors, metadata)
            
            for cluster in clusters:
                if cluster.size >= 3: # Min cluster size to generate knowledge
                    knowledge = self.knowledge_generator.generate_from_cluster(cluster)
                    if knowledge:
                        self.knowledge_repo.save(knowledge)
                        
            # Keep rolling buffer
            self.experience_buffer = self.experience_buffer[-10:]
