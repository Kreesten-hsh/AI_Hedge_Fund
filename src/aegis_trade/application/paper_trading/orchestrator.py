import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Awaitable

from aegis_trade.application.paper_trading.interfaces import IPaperBroker, IMarketFeed
from aegis_trade.domain.core import MarketBar, Symbol
from aegis_trade.domain.paper.models import (
    ActionType,
    OrderType,
    PaperExecutionReport,
    PaperOrder,
    PaperPortfolioSnapshot,
)
from aegis_trade.engine.events import (
    EngineEvent,
    FillEvent,
    MarketEvent,
    MetricsEvent,
    OrderAction,
    OrderEvent,
    SignalEvent,
)
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import PortfolioEngine
from aegis_trade.engine.risk_gate import (
    RISK_DECISION_KEY,
    OrderRejectedByRisk,
    RiskGate,
)
from aegis_trade.application.council.feature_provider import RollingFeatureProvider
from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.domain.core import Tick
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
        policy_store: IPolicyStore,
        feature_provider: RollingFeatureProvider
    ):
        self.broker = broker
        self.feed = feed
        self.risk_manager = risk_manager
        self.portfolio_engine = portfolio_engine
        self.event_publisher = event_publisher
        self.council = council
        self.policy_store = policy_store

        # Sans source de features, tous les agents votent WAIT et le système
        # tourne à vide en paraissant sain. Le paramètre est donc obligatoire :
        # l'échec doit survenir à la construction, pas en séance.
        self.feature_provider = feature_provider

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
        self.latest_snapshot: PaperPortfolioSnapshot | None = None

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

    async def _process_bar(self, bar: MarketBar) -> None:
        latest_prices = {bar.symbol: Decimal(str(bar.close))}

        # Le prix observé alimente d'abord le portefeuille : c'est lui que le
        # RiskEngine interroge. Fait avant toute décision, sinon le Council
        # voterait sur une equity et un drawdown périmés d'un tick.
        self.observe_market(bar)

        # Tell broker the current market price (for simulations of Limit/Stop/Market orders)
        if hasattr(self.broker, 'update_market_price'):
            self.broker.update_market_price(bar.close)

        # 1. Features réelles du marché observé. Les constantes précédentes ne
        # correspondaient à aucune clé lue par les agents : buy_score et
        # sell_score restaient nuls, le verdict était WAIT et aucun ordre
        # n'était atteignable, quel que soit le marché.
        context = MarketContext(
            symbol=bar.symbol,
            features=self.feature_provider.observe_bar(bar),
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

        report = await self.broker.submit_order(paper_order)

        # Seule latence réellement mesurée du système. `ExecutionAgent` lit
        # `broker_latency_ms` : sans cette remontée, il vote WAIT 0.0 en
        # permanence et ne peut jamais opposer son veto à un broker dégradé.
        execution = getattr(report, "execution", None)
        if execution is not None:
            self.feature_provider.observe_latency(float(execution.latency_ms))

        # Boucle de retour : sans elle, la position existe chez le broker mais
        # pas dans le portefeuille qui sert au calcul de risque.
        self._apply_report_fills(report)
        return report

    def _apply_report_fills(self, report: PaperExecutionReport) -> None:
        """Applique au portefeuille les fills réellement rapportés par le broker.

        On lit les fills du rapport plutôt que l'ordre soumis : un ordre peut
        être partiellement exécuté, et créditer le volume demandé plutôt que le
        volume obtenu fausserait l'exposition.
        """
        for fill in getattr(report, "fills", None) or []:
            self.observe_fill(
                symbol=fill.symbol,
                action=OrderAction.BUY if fill.action == ActionType.BUY else OrderAction.SELL,
                volume=fill.volume,
                price=fill.price,
                commission=fill.commission,
                timestamp=fill.timestamp,
            )

    async def process_signal(self, signal: SignalEvent):
        """[DEPRECATED] Processes a trading signal from a strategy."""
        logger.warning("process_signal is deprecated. Council handles signal generation via _process_feed.")

    def observe_tick(self, tick: Tick) -> None:
        """Point d'entrée unique d'une cotation réelle dans le système.

        Le spread ne peut venir que d'un tick : `MarketBar` ne porte pas de
        bid/ask, et le fabriquer à partir d'une barre remplacerait un
        placeholder par un autre. Le broker reçoit la même cotation dans le
        même appel : alimenter l'un sans l'autre ferait voter le Council sur
        un spread que le broker n'a jamais eu, ou ferait refuser l'exécution
        (`NoMarketDataError`) alors que le Council vient de décider.
        """
        self.feature_provider.observe_tick(tick)

        broker_observe = getattr(self.broker, "observe_tick", None)
        if callable(broker_observe):
            broker_observe(tick)

    def observe_market(self, bar: MarketBar) -> None:
        """Pousse un prix observé dans le portefeuille du RiskEngine.

        Le kill switch lit `portfolio.equity` et `portfolio.equity_curve`. Sans
        ce mark-to-market, l'equity reste figée au capital initial : le
        drawdown est structurellement nul et le kill switch ne peut jamais
        s'armer, quelles que soient les pertes réelles.
        """
        self.portfolio_engine.on_market_event(MarketEvent(timestamp=bar.timestamp, bar=bar))

    def observe_fill(
        self,
        *,
        symbol: Symbol,
        action: OrderAction,
        volume: Decimal,
        price: Decimal,
        commission: Decimal,
        timestamp: datetime,
    ) -> None:
        """Applique un fill exécuté au portefeuille du RiskEngine.

        Sans cette étape, une position ouverte chez le broker n'existe pas
        pour le calcul de risque : l'exposition mesurée reste nulle.
        """
        self.portfolio_engine.on_fill_event(
            FillEvent(
                timestamp=timestamp,
                symbol=symbol,
                action=action,
                volume=volume,
                fill_price=price,
                commission=commission,
                exchange="PAPER",
                strategy_id="paper_trading",
            )
        )

    def build_snapshot(self) -> PaperPortfolioSnapshot:
        """Photographie l'état réel du portefeuille.

        Toutes les grandeurs sont dérivées du `PortfolioEngine`, qui fait
        autorité (Lot 3). Le snapshot ne recalcule rien pour son propre compte :
        un dashboard qui diverge du RiskEngine afficherait un risque rassurant
        pendant que le kill switch s'arme, ou l'inverse.
        """
        portfolio = self.portfolio_engine
        equity = portfolio.equity

        # Le HWM se lit sur la courbe, pas sur le capital initial : un compte
        # en gain puis en repli est bien en drawdown.
        hwm = Decimal(str(portfolio.initial_capital))
        for point in portfolio.equity_curve:
            if point.equity > hwm:
                hwm = point.equity

        drawdown = 0.0
        if hwm > 0 and equity < hwm:
            drawdown = float((hwm - equity) / hwm * 100)

        gross_exposure = Decimal("0.0")
        net_exposure = Decimal("0.0")
        floating_pnl = Decimal("0.0")
        for symbol, position in portfolio.open_positions.items():
            price = portfolio.get_latest_price(symbol)
            if price is None:
                # Une position sans prix observé n'est pas comptée à zéro : ce
                # serait sous-estimer l'exposition. Elle est ignorée du calcul
                # et le restera jusqu'au premier tick sur cet instrument.
                continue
            notional = position.volume * price
            gross_exposure += abs(notional)
            net_exposure += notional
            floating_pnl += position.unrealized_pnl

        return PaperPortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            balance=portfolio.cash,
            equity=equity,
            drawdown=drawdown,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            open_positions_count=len(portfolio.open_positions),
            margin_used=Decimal("0.0"),
            daily_pnl=equity - Decimal(str(portfolio.initial_capital)),
            floating_pnl=floating_pnl,
        )

    def refresh_snapshot(self) -> PaperPortfolioSnapshot:
        """Rafraîchit le snapshot exposé au dashboard."""
        self.latest_snapshot = self.build_snapshot()
        return self.latest_snapshot

    async def publish_snapshot(self) -> PaperPortfolioSnapshot:
        """Rafraîchit puis publie le snapshot sur le bus.

        L'ancienne boucle calculait la valeur puis l'abandonnait (`_ = snapshot`) :
        aucun consommateur ne pouvait voir le portefeuille évoluer.
        """
        snapshot = self.refresh_snapshot()
        await self.event_publisher(
            MetricsEvent(
                timestamp=snapshot.timestamp,
                metrics={
                    "equity": float(snapshot.equity),
                    "balance": float(snapshot.balance),
                    "drawdown_pct": snapshot.drawdown,
                    "gross_exposure": float(snapshot.gross_exposure),
                    "net_exposure": float(snapshot.net_exposure),
                    "floating_pnl": float(snapshot.floating_pnl),
                    "open_positions": float(snapshot.open_positions_count),
                },
            )
        )
        return snapshot

    async def _monitor_portfolio_loop(self):
        """Boucle de fond : publie un snapshot réel à intervalle régulier."""
        while self.is_running:
            await asyncio.sleep(5.0)
            try:
                await self.publish_snapshot()
            except Exception:
                # Le monitoring ne doit jamais tuer la session de trading, mais
                # un échec silencieux ferait croire que le risque est surveillé.
                logger.exception("Portfolio snapshot failed; risk view is stale.")
