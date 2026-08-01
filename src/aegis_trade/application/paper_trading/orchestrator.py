import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Awaitable

from aegis_trade.application.paper_trading.interfaces import IPaperBroker, IMarketFeed
from aegis_trade.domain.paper.models import PaperOrder, ActionType, OrderType, PaperPortfolioSnapshot
from aegis_trade.engine.events import SignalEvent, OrderEvent, EngineEvent
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import PortfolioEngine
from aegis_trade.engine.risk_gate import (
    RISK_DECISION_KEY,
    OrderRejectedByRisk,
    RiskGate,
)
from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.domain.rl import IPolicyStore, PolicyDecision
from aegis_trade.domain.council import MarketContext
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PaperTradingOrchestrator:
    def __init__(
        self,
        broker: IPaperBroker,
        feed: IMarketFeed,
        risk_manager: GlobalRiskManager,
        portfolio_engine: PortfolioEngine,
        event_publisher: Callable[[EngineEvent], Awaitable[None]],
        council: MultiAgentCouncil,
        policy_store: IPolicyStore
    ):
        self.broker = broker
        self.feed = feed
        self.risk_manager = risk_manager
        self.portfolio_engine = portfolio_engine
        self.event_publisher = event_publisher
        self.council = council
        self.policy_store = policy_store

        # Toute soumission passe par cette porte. `risk_manager` reste exposé
        # pour le kill switch de l'API, mais plus aucun chemin ne l'appelle
        # directement pour valider un ordre.
        self.risk_gate = RiskGate(risk_manager, portfolio_engine)

        self._monitoring_task = None
        self._market_feed_task = None
        self.is_running = False
        
        # Dashboard exposure
        self.latest_verdict = None
        self.latest_policy = None

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
        """Consumes the market feed, evaluates signals via Council, and executes through GlobalRiskManager."""
        async for bar in self.feed.subscribe():
            if not self.is_running:
                break
            try:
                await self._process_bar(bar)
            except OrderRejectedByRisk as rejection:
                # Refus normal du RiskEngine : on continue à consommer le flux.
                logger.info("Order rejected by Risk Manager: %s", rejection.reason)
            except Exception:
                # Toute autre erreur est un défaut de code ou de données. Elle
                # arrête la boucle : une tâche asyncio qui meurt en silence est
                # pire qu'un arrêt visible (le système croirait trader).
                logger.exception("Fatal error in market feed loop; halting the loop.")
                self.is_running = False
                raise

    async def _process_bar(self, bar) -> None:
        latest_prices = {bar.symbol: Decimal(str(bar.close))}

        # Tell broker the current market price (for simulations of Limit/Stop/Market orders)
        if hasattr(self.broker, 'update_market_price'):
            self.broker.update_market_price(bar.close)

        # 1. Build MarketContext (MVP placeholders for now until FeatureExtractor is built)
        context = MarketContext(
            symbol=bar.symbol,
            features={
                "trend_score": 0.5,
                "momentum_score": 0.5,
                "volatility_score": 0.5,
                "liquidity_score": 0.5,
                "pattern_score": 0.5,
                "news_score": 0.5,
                "portfolio_risk": 0.5,
                "execution_cost": 0.5,
                "rsi": 55.0,
                "ema_distance": 0.1,
                "atr": 1.5
            },
            portfolio=self.portfolio_engine,
            latest_prices=latest_prices,
            memory_score=0.0
        )

        # 2. Retrieve Active RL Policy
        policy_decision = None
        active_model = self.policy_store.load_active_policy()
        if active_model:
            try:
                # MVP: Dummy observation of 30 zeros until FeatureExtractor provides state vector
                obs = np.zeros(30, dtype=np.float32)
                action, _ = active_model.predict(obs, deterministic=True)
                policy_decision = PolicyDecision(
                    risk_multiplier=float(action[0]),
                    confidence_threshold_adjustment=float(action[1]),
                    agent_weights={
                        "Trend": float(action[2]),
                        "Momentum": float(action[3]),
                        "Volatility": float(action[4]),
                        "Liquidity": float(action[5]),
                        "Pattern": float(action[6]),
                        "News": float(action[7]),
                        "Portfolio": float(action[8]),
                        "Execution": float(action[9]),
                    }
                )
            except Exception as e:
                logger.error(f"Error extracting policy decision from active model: {e}")
                policy_decision = None

        # 3. Council Evaluation
        verdict = self.council.evaluate(context, policy_decision)

        # Save for dashboard
        self.latest_policy = policy_decision
        self.latest_verdict = verdict

        # 4. Generate OrderEvent if verdict is actionable
        base_volume = 1.0  # Base size to be scaled by council/RL
        order_event = self.council.create_order(verdict, bar.symbol, base_volume, context)

        if not order_event:
            return

        # 5/6/7. Validation puis soumission — un seul chemin pour tout le système.
        await self.submit_order(order_event, latest_prices)

    async def submit_order(
        self,
        order_event: OrderEvent,
        latest_prices: dict | None = None,
        order_id: str | None = None,
    ):
        """Point d'entrée unique de toute soumission d'ordre.

        Lève `OrderRejectedByRisk` si le RiskEngine refuse : aucun appelant ne
        peut soumettre sans passer par ce check, y compris l'API.
        """
        risk_decision = self.risk_gate.authorize(order_event, latest_prices)

        # La décision voyage avec l'ordre : le broker inscrit dans son rapport
        # ce que le RiskEngine a réellement dit, pas une constante d'affichage.
        context_features = dict(getattr(order_event, "context_features", {}) or {})
        context_features[RISK_DECISION_KEY] = risk_decision

        paper_order = PaperOrder(
            order_id=order_id or f"ORD-{datetime.now().timestamp()}",
            symbol=order_event.symbol,
            action=ActionType.BUY if order_event.action.value.upper() == "BUY" else ActionType.SELL,
            order_type=OrderType.MARKET,
            volume=Decimal(str(order_event.volume)),
            timestamp=datetime.now(timezone.utc),
            context_features=context_features
        )

        return await self.broker.submit_order(paper_order)

    async def process_signal(self, signal: SignalEvent):
        """[DEPRECATED] Processes a trading signal from a strategy."""
        logger.warning("process_signal is deprecated. Council handles signal generation via _process_feed.")

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
