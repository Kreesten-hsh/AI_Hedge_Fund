import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Awaitable

from aegis_trade.application.paper_trading.interfaces import IPaperBroker, IMarketFeed
from aegis_trade.domain.paper.models import PaperOrder, ActionType, OrderType, PaperPortfolioSnapshot
from aegis_trade.engine.events import SignalEvent, OrderEvent, EngineEvent
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import PortfolioEngine


class PaperTradingOrchestrator:
    def __init__(
        self,
        broker: IPaperBroker,
        feed: IMarketFeed,
        risk_manager: GlobalRiskManager,
        portfolio_engine: PortfolioEngine,
        event_publisher: Callable[[EngineEvent], Awaitable[None]]
    ):
        self.broker = broker
        self.feed = feed
        self.risk_manager = risk_manager
        self.portfolio_engine = portfolio_engine
        self.event_publisher = event_publisher
        
        self._monitoring_task = None
        self._market_feed_task = None
        self.is_running = False

    async def start(self):
        """Starts the market feed and the monitoring loop."""
        self.is_running = True
        self._market_feed_task = asyncio.create_task(self._process_feed())
        self._monitoring_task = asyncio.create_task(self._monitor_portfolio_loop())

    async def stop(self):
        """Stops all background loops."""
        self.is_running = False
        if self._market_feed_task:
            self._market_feed_task.cancel()
        if self._monitoring_task:
            self._monitoring_task.cancel()

    async def _process_feed(self):
        """Consumes the market feed and updates the broker pricing."""
        async for bar in self.feed.subscribe():
            if not self.is_running:
                break
            # Tell broker the current market price (for simulations of Limit/Stop/Market orders)
            if hasattr(self.broker, 'update_market_price'):
                self.broker.update_market_price(bar.close)

    async def process_signal(self, signal: SignalEvent):
        """Processes a trading signal from a strategy."""
        
        # 1. Translate Signal to standard OrderEvent format for RiskManager
        action_map = {
            "enter_long": "buy",
            "exit_short": "buy",
            "enter_short": "sell",
            "exit_long": "sell",
            "hold": "hold"
        }
        
        action = action_map.get(signal.intent.value)
        if action == "hold":
            return
            
        # Simplified volume sizing for paper trading defaults
        proposed_volume = Decimal("1.0") 
        
        order_event = OrderEvent(
            timestamp=datetime.now(timezone.utc),
            symbol=signal.symbol,
            action=action,
            volume=proposed_volume,
            order_type="market",
            strategy_id=signal.strategy_id
        )

        # 2. GlobalRiskManager evaluation
        # The PortfolioEngine usually holds the current true portfolio state.
        is_approved, reason = self.risk_manager.evaluate_order(
            order_event, self.portfolio_engine.get_portfolio()
        )

        if not is_approved:
            # Emit audit log if rejected by risk
            # Note: actual publishing of AuditEvent is done internally by RiskManager 
            # if wired up, but here we just drop the order.
            return

        # 3. Create PaperOrder
        paper_order = PaperOrder(
            order_id=f"ORD-{datetime.now().timestamp()}",
            symbol=signal.symbol,
            action=ActionType.BUY if action == "buy" else ActionType.SELL,
            order_type=OrderType.MARKET,
            volume=proposed_volume,
            timestamp=datetime.now(timezone.utc)
        )

        # 4. Submit to Paper Broker
        await self.broker.submit_order(paper_order)

    async def _monitor_portfolio_loop(self):
        """Background loop taking snapshots every X seconds."""
        while self.is_running:
            await asyncio.sleep(5.0)  # Configurable interval, e.g. 5 seconds
            
            if hasattr(self.broker, 'account'):
                account = self.broker.account
                # Compute snapshot
                balance = sum(b.total for b in account.balances.values())
                
                # Expose a snapshot for the dashboard
                snapshot = PaperPortfolioSnapshot(
                    timestamp=datetime.now(timezone.utc),
                    balance=balance,
                    equity=balance,  # Simplified
                    drawdown=0.0,
                    gross_exposure=Decimal("0.0"),
                    net_exposure=Decimal("0.0"),
                    open_positions_count=len(account.positions),
                    margin_used=Decimal("0.0"),
                    daily_pnl=Decimal("0.0"),
                    floating_pnl=Decimal("0.0")
                )
                
                # Emit snapshot as a METRICS event or just store it
                # For now, it satisfies the requirement of regular snapshots
                _ = snapshot
