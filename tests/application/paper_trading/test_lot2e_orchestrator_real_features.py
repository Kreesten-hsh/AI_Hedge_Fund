"""Lot 2E — l'orchestrateur alimente le Council en features réelles.

Le contrat de clés est vérifié dans
`tests/application/council/test_lot2e_agent_feature_contract.py`. Ce fichier
vérifie la moitié restante : que l'orchestrateur **utilise** ce fournisseur au
lieu du dictionnaire de constantes qu'il injectait
(`trend_score: 0.5`, ... `rsi: 55.0`, `ema_distance: 0.1`, `atr: 1.5`).

C'est ici que se joue le critère de sortie du Lot 2 : « un tick réel produit un
vote non nul d'au moins un agent ». Avec les constantes, `buy_score` et
`sell_score` valaient tous deux 0, `ConflictResolver` renvoyait un
multiplicateur nul, le verdict devenait WAIT et `create_order` renvoyait None —
aucun ordre n'était atteignable, quel que soit le marché.

Les agents, le Council, l'extracteur, le `PortfolioEngine` et le
`GlobalRiskManager` sont les vrais. Seuls le broker et le flux sont doublés :
doubler le Council reviendrait à tester le double.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, AsyncGenerator, List

import pytest

from aegis_trade.application.council.agents.execution_agent import ExecutionAgent
from aegis_trade.application.council.agents.liquidity_agent import LiquidityAgent
from aegis_trade.application.council.agents.momentum_agent import MomentumAgent
from aegis_trade.application.council.agents.news_agent import NewsAgent
from aegis_trade.application.council.agents.pattern_agent import PatternAgent
from aegis_trade.application.council.agents.portfolio_agent import PortfolioAgent
from aegis_trade.application.council.agents.trend_agent import TrendAgent
from aegis_trade.application.council.agents.volatility_agent import VolatilityAgent
from aegis_trade.application.council.feature_provider import RollingFeatureProvider
from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.application.paper_trading.interfaces import IMarketFeed, IPaperBroker
from aegis_trade.application.paper_trading.orchestrator import PaperTradingOrchestrator
from aegis_trade.domain.core import AssetClass, MarketBar, Symbol, TimeFrame, Tick
from aegis_trade.domain.council import CouncilVerdict, MarketContext
from aegis_trade.domain.paper.models import (
    PaperExecution,
    PaperExecutionReport,
    PaperFill,
    PaperOrder,
)
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import PortfolioEngine
from aegis_trade.infrastructure.features.technical_extractor import (
    TechnicalFeatureExtractor,
)

SYMBOL = Symbol(name="BTCUSD", asset_class=AssetClass.CRYPTO)
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)

PLACEHOLDER_KEYS = (
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
    "pattern_score",
    "news_score",
    "portfolio_risk",
    "execution_cost",
)


def _bar(close: str, index: int, symbol: Symbol = SYMBOL) -> MarketBar:
    price = Decimal(close)
    return MarketBar(
        symbol=symbol,
        timeframe=TimeFrame.M1,
        timestamp=BASE + timedelta(minutes=index),
        open=price,
        high=price + Decimal("1"),
        low=price - Decimal("1"),
        close=price,
        volume=Decimal("1000"),
    )


class RecordingBroker(IPaperBroker):
    """Broker doublé qui conserve les ordres et renvoie un rapport complet.

    `latency_ms` est fixée ici parce que c'est la seule valeur mesurée par un
    vrai broker : le test vérifie qu'elle remonte jusqu'aux features, pas
    qu'elle soit exacte.
    """

    def __init__(self, latency_ms: float = 137.0) -> None:
        self.orders: List[PaperOrder] = []
        self.ticks: List[Tick] = []
        self.latency_ms = latency_ms

    async def submit_order(self, order: PaperOrder) -> PaperExecutionReport:
        self.orders.append(order)
        moment = datetime.now(timezone.utc)
        return PaperExecutionReport(
            timestamp=moment,
            order=order,
            risk_decision="APPROVED_BY_RISK_ENGINE",
            execution=PaperExecution(
                execution_id=f"EXEC-{order.order_id}",
                order_id=order.order_id,
                timestamp=moment,
                requested_price=Decimal("100"),
                execution_price=Decimal("100"),
                slippage=Decimal("0"),
                latency_ms=self.latency_ms,
            ),
            fills=[
                PaperFill(
                    fill_id=f"FILL-{order.order_id}",
                    order_id=order.order_id,
                    symbol=order.symbol,
                    action=order.action,
                    volume=order.volume,
                    price=Decimal("100"),
                    commission=Decimal("0"),
                    timestamp=moment,
                )
            ],
        )

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def cancel_all_orders(self) -> int:
        return 0

    async def close_all_positions(self) -> int:
        return 0

    def observe_tick(self, tick: Tick) -> None:
        self.ticks.append(tick)


class ReplayFeed(IMarketFeed):
    def __init__(self, bars: List[MarketBar]) -> None:
        self.bars = bars

    async def subscribe(self) -> AsyncGenerator[MarketBar, None]:
        for bar in self.bars:
            yield bar


class RecordingCouncil(MultiAgentCouncil):
    """Vrai Council, mais qui conserve les contextes réellement reçus.

    Le contrat porte sur ce que l'orchestrateur *envoie* : un double du Council
    ne prouverait rien sur les votes.
    """

    def __init__(self, agents: List[Any]) -> None:
        super().__init__(agents=agents)
        self.contexts: List[MarketContext] = []
        self.verdicts: List[CouncilVerdict] = []

    def evaluate(self, context: MarketContext, policy: Any = None) -> CouncilVerdict:
        self.contexts.append(context)
        verdict = super().evaluate(context, policy)
        self.verdicts.append(verdict)
        return verdict


class NullPolicyStore:
    def load_active_policy(self) -> None:
        return None

    def save_policy(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        raise NotImplementedError

    def list_policies(self) -> List[Any]:  # pragma: no cover
        return []


def _agents() -> List[Any]:
    return [
        TrendAgent(),
        MomentumAgent(),
        VolatilityAgent(),
        LiquidityAgent(),
        PatternAgent(),
        PortfolioAgent(),
        ExecutionAgent(),
        NewsAgent(),
    ]


def _build(
    bars: List[MarketBar] | None = None,
    broker: RecordingBroker | None = None,
) -> tuple[PaperTradingOrchestrator, RecordingCouncil, RecordingBroker]:
    council = RecordingCouncil(agents=_agents())
    broker = broker or RecordingBroker()
    risk_manager = GlobalRiskManager(max_drawdown=Decimal("0.05"))
    portfolio = PortfolioEngine(initial_capital=100_000.0, risk_manager=risk_manager)

    async def publisher(event: Any) -> None:
        return None

    orchestrator = PaperTradingOrchestrator(
        broker=broker,
        feed=ReplayFeed(bars or []),
        risk_manager=risk_manager,
        portfolio_engine=portfolio,
        event_publisher=publisher,
        council=council,
        policy_store=NullPolicyStore(),
        feature_provider=RollingFeatureProvider(extractor=TechnicalFeatureExtractor()),
    )
    return orchestrator, council, broker


def _uptrend(count: int = 60) -> List[MarketBar]:
    return [_bar(str(100 + index), index) for index in range(count)]


class TestPlaceholderFeaturesAreGone:
    @pytest.mark.asyncio
    async def test_dead_score_keys_never_reach_the_council(self) -> None:
        orchestrator, council, _ = _build()

        for bar in _uptrend(25):
            await orchestrator._process_bar(bar)

        assert council.contexts
        for context in council.contexts:
            for dead in PLACEHOLDER_KEYS:
                assert dead not in context.features

    @pytest.mark.asyncio
    async def test_rsi_is_no_longer_the_constant_that_forced_wait(self) -> None:
        """55.0 tombait dans la bande neutre 30-70 à chaque tick.

        Le MomentumAgent ne pouvait donc mathématiquement jamais voter autre
        chose que WAIT.
        """
        orchestrator, council, _ = _build()

        for bar in _uptrend(60):
            await orchestrator._process_bar(bar)

        last = council.contexts[-1].features
        assert last["rsi"] != pytest.approx(55.0)
        assert last["rsi"] > 70.0

    @pytest.mark.asyncio
    async def test_features_move_between_two_bars(self) -> None:
        orchestrator, council, _ = _build()

        for bar in _uptrend(30):
            await orchestrator._process_bar(bar)

        assert council.contexts[-1].features["ema_50"] != (
            council.contexts[-2].features["ema_50"]
        )


class TestLotTwoExitCriterion:
    """« Un tick réel produit un vote non nul d'au moins un agent. »"""

    @pytest.mark.asyncio
    async def test_at_least_one_agent_votes_with_non_zero_confidence(self) -> None:
        orchestrator, council, _ = _build()

        for bar in _uptrend(60):
            await orchestrator._process_bar(bar)

        votes = council.verdicts[-1].votes
        actionable = [v for v in votes if v.vote != "WAIT" and v.confidence > 0.0]
        assert actionable, f"tous les agents ont voté WAIT : {votes}"

    @pytest.mark.asyncio
    async def test_the_verdict_becomes_actionable(self) -> None:
        orchestrator, council, _ = _build()

        for bar in _uptrend(60):
            await orchestrator._process_bar(bar)

        assert council.verdicts[-1].final_vote in ("BUY", "SELL")
        assert council.verdicts[-1].position_size_multiplier > 0.0

    @pytest.mark.asyncio
    async def test_an_order_actually_reaches_the_broker(self) -> None:
        """Le bout de la chaîne : verdict -> create_order -> RiskGate -> broker."""
        bars = _uptrend(60)
        orchestrator, _, broker = _build(bars=bars)

        for bar in bars:
            await orchestrator._process_bar(bar)

        assert broker.orders, "aucun ordre soumis sur 60 barres de tendance franche"

    @pytest.mark.asyncio
    async def test_the_order_carries_the_real_features(self) -> None:
        """`context_features` voyage jusqu'au rapport d'exécution.

        C'est la trace d'audit du trade : y recopier des constantes rendrait
        toute analyse post-mortem fausse.
        """
        bars = _uptrend(60)
        orchestrator, _, broker = _build(bars=bars)

        for bar in bars:
            await orchestrator._process_bar(bar)

        carried = broker.orders[-1].context_features
        assert "rsi" in carried
        for dead in PLACEHOLDER_KEYS:
            assert dead not in carried


class TestWarmUpDoesNotFabricateAVote:
    @pytest.mark.asyncio
    async def test_first_bar_yields_no_order(self) -> None:
        """Sans RSI ni bandes définies, les agents doivent voter WAIT.

        Un ordre émis sur la première barre signifierait qu'une valeur a été
        fabriquée pour combler la chauffe des fenêtres.
        """
        orchestrator, council, broker = _build()

        await orchestrator._process_bar(_bar("100", 0))

        assert broker.orders == []
        assert council.verdicts[-1].final_vote == "WAIT"

    @pytest.mark.asyncio
    async def test_undefined_bands_are_absent_rather_than_zero(self) -> None:
        orchestrator, council, _ = _build()

        await orchestrator._process_bar(_bar("100", 0))

        assert "bb_upper" not in council.contexts[-1].features


class TestRealSourcesForTheRemainingAgents:
    @pytest.mark.asyncio
    async def test_observed_tick_publishes_the_spread(self) -> None:
        """Le spread ne peut venir que d'un tick : `MarketBar` n'a pas de bid/ask."""
        orchestrator, council, _ = _build()

        orchestrator.observe_tick(
            Tick(
                symbol=SYMBOL,
                timestamp=BASE,
                bid=Decimal("99.5"),
                ask=Decimal("100.5"),
            )
        )
        await orchestrator._process_bar(_bar("100", 0))

        assert council.contexts[-1].features["spread"] == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_observed_tick_also_reaches_the_broker(self) -> None:
        """Le broker refuse d'exécuter sans cotation observée (Lot 2B).

        Un point d'entrée unique évite que le runner alimente l'un et oublie
        l'autre : le Council verrait un spread que le broker n'a jamais eu.
        """
        orchestrator, _, broker = _build()
        tick = Tick(
            symbol=SYMBOL,
            timestamp=BASE,
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
        )

        orchestrator.observe_tick(tick)

        assert broker.ticks == [tick]

    @pytest.mark.asyncio
    async def test_measured_execution_latency_reaches_the_features(self) -> None:
        """`ExecutionAgent` lit `broker_latency_ms` ; la seule source réelle est
        la latence mesurée sur une exécution (`PaperExecution.latency_ms`)."""
        bars = _uptrend(60)
        broker = RecordingBroker(latency_ms=137.0)
        orchestrator, council, _ = _build(bars=bars, broker=broker)

        for bar in bars:
            await orchestrator._process_bar(bar)

        assert broker.orders, "le test suppose au moins une exécution"
        assert council.contexts[-1].features["broker_latency_ms"] == pytest.approx(
            137.0
        )


class TestTheProviderIsMandatory:
    def test_orchestrator_cannot_be_built_without_a_feature_source(self) -> None:
        """Pas de repli silencieux.

        Un défaut à `None` produirait un dictionnaire de features vide : tous
        les agents voteraient WAIT et le système paraîtrait sain en tournant à
        vide. L'échec doit être à la construction, pas à 3 h du matin.
        """
        risk_manager = GlobalRiskManager(max_drawdown=Decimal("0.05"))

        async def publisher(event: Any) -> None:
            return None

        with pytest.raises(TypeError):
            PaperTradingOrchestrator(  # type: ignore[call-arg]
                broker=RecordingBroker(),
                feed=ReplayFeed([]),
                risk_manager=risk_manager,
                portfolio_engine=PortfolioEngine(
                    initial_capital=100_000.0, risk_manager=risk_manager
                ),
                event_publisher=publisher,
                council=RecordingCouncil(agents=_agents()),
                policy_store=NullPolicyStore(),
            )
