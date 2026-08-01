"""Lot 2B — le fill vient du marché, la décision de risque vient du RiskEngine.

Deux façades supprimées par ce lot (`docs/refont/PLAN_DE_CORRECTION.md`) :

1. le prix de fill constant, qui produisait un P&L faux donc un drawdown faux ;
2. `risk_decision="APPROVED"` écrit en dur, qui faisait signer au RiskEngine
   des ordres qu'il n'avait jamais vus.

Les tests portent sur la valeur observée par l'audit — le contenu du rapport
d'exécution — et non sur le fait qu'un appel ait été fait : un appel effectué
puis ignoré laissait déjà passer les deux façades.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from aegis_trade.application.council.feature_provider import RollingFeatureProvider
from aegis_trade.application.paper_trading.interfaces import (
    ICommissionModel,
    IExecutionReportRepository,
    ILatencyModel,
    ISlippageModel,
)
from aegis_trade.domain.core import AssetClass, Symbol, Tick
from aegis_trade.domain.paper.models import (
    ActionType,
    OrderType,
    PaperAccount,
    PaperBalance,
    PaperExecutionReport,
    PaperOrder,
)
from aegis_trade.engine.events import OrderAction, OrderEvent
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import PortfolioEngine
from aegis_trade.engine.risk_gate import (
    RISK_DECISION_APPROVED,
    RISK_DECISION_KEY,
    RISK_DECISION_UNRECORDED,
    OrderRejectedByRisk,
    RiskGate,
    recorded_decision,
)
from aegis_trade.infrastructure.features.technical_extractor import (
    TechnicalFeatureExtractor,
)
from aegis_trade.infrastructure.paper.broker import PaperBroker
from aegis_trade.infrastructure.paper.deriv_gateway import DerivGateway, NoMarketDataError

SYMBOL = Symbol(name="frxEURUSD", asset_class=AssetClass.FOREX)
BID = Decimal("1.08549")
ASK = Decimal("1.08553")


def _order(action: ActionType, context_features: dict | None = None) -> PaperOrder:
    return PaperOrder(
        order_id="ORD-1",
        symbol=SYMBOL,
        action=action,
        order_type=OrderType.MARKET,
        volume=Decimal("1.0"),
        timestamp=datetime.now(timezone.utc),
        context_features=context_features or {},
    )


def _tick() -> Tick:
    return Tick(
        symbol=SYMBOL,
        timestamp=datetime.now(timezone.utc),
        bid=BID,
        ask=ASK,
    )


def _gateway() -> DerivGateway:
    gateway = DerivGateway(token="demo_token")
    gateway.api = None  # Mode hors-ligne : le prix ne peut venir que d'un tick.
    return gateway


# --- 1. Le prix de fill vient du marché, ou l'ordre ne part pas ------------


@pytest.mark.anyio
async def test_submit_without_observed_tick_refuses_instead_of_inventing_a_price() -> None:
    with pytest.raises(NoMarketDataError, match="Aucune cotation observée"):
        await _gateway().submit_order(_order(ActionType.BUY))


@pytest.mark.anyio
async def test_buy_fills_at_ask_and_sell_fills_at_bid() -> None:
    """Le spread est traversé dans le bon sens.

    Exécuter un achat au bid offrirait un demi-spread gratuit à chaque ordre,
    ce qui suffit à rendre « rentable » une stratégie perdante.
    """
    gateway = _gateway()
    gateway.observe_tick(_tick())

    buy = await gateway.submit_order(_order(ActionType.BUY))
    sell = await gateway.submit_order(_order(ActionType.SELL))

    assert buy.fills[0].price == ASK
    assert sell.fills[0].price == BID
    assert buy.fills[0].price != sell.fills[0].price


@pytest.mark.anyio
async def test_fill_price_follows_the_tick_it_is_not_a_constant() -> None:
    gateway = _gateway()

    gateway.observe_tick(_tick())
    first = await gateway.submit_order(_order(ActionType.BUY))

    moved = Tick(
        symbol=SYMBOL,
        timestamp=datetime.now(timezone.utc),
        bid=BID + Decimal("0.01"),
        ask=ASK + Decimal("0.01"),
    )
    gateway.observe_tick(moved)
    second = await gateway.submit_order(_order(ActionType.BUY))

    assert second.fills[0].price == moved.ask
    assert second.fills[0].price - first.fills[0].price == Decimal("0.01")


class _FakeDerivApi:
    """API Deriv doublée : renvoie la réponse `buy` qu'on lui donne."""

    def __init__(self, response: Any) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    async def buy(self, request: dict[str, Any]) -> Any:
        self.requests.append(request)
        return self.response


def _connected_gateway(response: Any) -> tuple[DerivGateway, _FakeDerivApi]:
    gateway = DerivGateway(token="demo_token")
    api = _FakeDerivApi(response)
    gateway.api = api
    gateway._is_virtual_confirmed = True
    gateway.observe_tick(_tick())
    return gateway, api


@pytest.mark.anyio
async def test_fill_price_comes_from_the_broker_response_not_the_local_quote() -> None:
    """Le prix réellement obtenu prime sur le prix attendu.

    L'écart entre les deux est le slippage : le figer à zéro reviendrait à
    supposer une exécution parfaite, hypothèse qui flatte tout backtest.
    """
    executed = Decimal("1.08571")
    gateway, api = _connected_gateway({"buy": {"buy_price": float(executed)}})

    report = await gateway.submit_order(_order(ActionType.BUY))

    assert report.fills[0].price == executed
    assert report.execution is not None
    assert report.execution.requested_price == ASK
    assert report.execution.slippage == executed - ASK
    assert api.requests[0]["parameters"]["symbol"] == SYMBOL.name
    assert api.requests[0]["parameters"]["contract_type"] == "CALL"


@pytest.mark.anyio
async def test_broker_response_without_price_refuses_instead_of_falling_back() -> None:
    gateway, _ = _connected_gateway({"buy": {"contract_id": 42}})

    with pytest.raises(NoMarketDataError, match="buy_price"):
        await gateway.submit_order(_order(ActionType.BUY))


@pytest.mark.anyio
async def test_sell_order_is_sent_as_a_put_contract() -> None:
    gateway, api = _connected_gateway({"buy": {"buy_price": 1.085}})

    await gateway.submit_order(_order(ActionType.SELL))

    assert api.requests[0]["parameters"]["contract_type"] == "PUT"
    assert api.requests[0]["price"] == pytest.approx(float(BID))



# --- 2. La décision de risque est celle du RiskEngine ----------------------

def test_recorded_decision_never_promotes_an_absent_trace_to_an_approval() -> None:
    assert recorded_decision(None) == RISK_DECISION_UNRECORDED
    assert recorded_decision({}) == RISK_DECISION_UNRECORDED
    assert recorded_decision({RISK_DECISION_KEY: ""}) == RISK_DECISION_UNRECORDED
    assert recorded_decision({RISK_DECISION_KEY: 1}) == RISK_DECISION_UNRECORDED
    assert recorded_decision({"other": "APPROVED"}) == RISK_DECISION_UNRECORDED
    assert (
        recorded_decision({RISK_DECISION_KEY: RISK_DECISION_APPROVED})
        == RISK_DECISION_APPROVED
    )


def test_authorize_returns_the_verdict_so_it_can_be_carried_to_the_broker() -> None:
    risk_manager = GlobalRiskManager()
    portfolio = PortfolioEngine(initial_capital=10_000.0, risk_manager=risk_manager)
    gate = RiskGate(risk_manager, portfolio)

    order = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        symbol=SYMBOL,
        action=OrderAction.BUY,
        volume=Decimal("1.0"),
        order_type="market",
        strategy_id="lot2b",
    )

    assert gate.authorize(order, {SYMBOL: ASK}) == RISK_DECISION_APPROVED

    risk_manager._emergency_halt_active = True
    with pytest.raises(OrderRejectedByRisk):
        gate.authorize(order, {SYMBOL: ASK})


@pytest.mark.anyio
async def test_deriv_report_shows_unrecorded_when_the_risk_gate_was_bypassed() -> None:
    """Un ordre soumis directement au broker n'a pas vu le RiskEngine.

    Le rapport doit le montrer : c'est la seule façon qu'un contournement reste
    détectable à l'audit au lieu d'être maquillé en approbation.
    """
    gateway = _gateway()
    gateway.observe_tick(_tick())

    report = await gateway.submit_order(_order(ActionType.BUY))

    assert report.risk_decision == RISK_DECISION_UNRECORDED
    assert report.risk_decision != "APPROVED"


@pytest.mark.anyio
async def test_deriv_report_carries_the_real_verdict_when_the_gate_stamped_it() -> None:
    gateway = _gateway()
    gateway.observe_tick(_tick())

    order = _order(ActionType.BUY, {RISK_DECISION_KEY: RISK_DECISION_APPROVED})
    report = await gateway.submit_order(order)

    assert report.risk_decision == RISK_DECISION_APPROVED


# --- 3. Le PaperBroker lit la même trace ----------------------------------


class _NoSlippage(ISlippageModel):
    def calculate_slippage(self, order: PaperOrder, market_price: Decimal) -> Decimal:
        return Decimal("0.0")


class _NoLatency(ILatencyModel):
    async def simulate_latency(self) -> float:
        return 0.0


class _NoCommission(ICommissionModel):
    def calculate_commission(self, order: PaperOrder, fill_price: Decimal) -> Decimal:
        return Decimal("0.0")


class _MemoryRepository(IExecutionReportRepository):
    def __init__(self) -> None:
        self.saved: list[PaperExecutionReport] = []

    def save(self, report: PaperExecutionReport) -> None:
        self.saved.append(report)

    def get_by_order_id(self, order_id: str) -> PaperExecutionReport | None:
        return next((r for r in self.saved if r.order.order_id == order_id), None)

    def get_all(self) -> list[PaperExecutionReport]:
        return list(self.saved)


def _paper_broker() -> tuple[PaperBroker, _MemoryRepository]:
    repository = _MemoryRepository()

    async def publisher(event: Any) -> None:
        return None

    account = PaperAccount(
        account_id="TEST",
        balances={
            "USD": PaperBalance(
                currency="USD",
                total=Decimal("10000.0"),
                locked=Decimal("0.0"),
                available=Decimal("10000.0"),
            )
        },
    )
    broker = PaperBroker(
        account=account,
        slippage_model=_NoSlippage(),
        latency_model=_NoLatency(),
        commission_model=_NoCommission(),
        repository=repository,
        event_publisher=publisher,
    )
    return broker, repository


@pytest.mark.anyio
async def test_paper_broker_report_is_unrecorded_without_a_risk_gate_stamp() -> None:
    broker, repository = _paper_broker()

    report = await broker.submit_order(_order(ActionType.BUY))

    assert report.risk_decision == RISK_DECISION_UNRECORDED
    assert repository.saved[-1].risk_decision == RISK_DECISION_UNRECORDED


@pytest.mark.anyio
async def test_paper_broker_report_carries_the_stamped_verdict() -> None:
    broker, _ = _paper_broker()

    order = _order(ActionType.BUY, {RISK_DECISION_KEY: RISK_DECISION_APPROVED})
    report = await broker.submit_order(order)

    assert report.risk_decision == RISK_DECISION_APPROVED


@pytest.mark.anyio
async def test_paper_broker_rejection_is_neither_approved_nor_unrecorded() -> None:
    """Un refus du broker reste distinct d'une absence de décision."""
    broker, _ = _paper_broker()

    too_big = PaperOrder(
        order_id="ORD-BIG",
        symbol=SYMBOL,
        action=ActionType.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("1000.0"),
        timestamp=datetime.now(timezone.utc),
    )
    report = await broker.submit_order(too_big)

    assert report.risk_decision.startswith("REJECTED:")


# --- 4. Bout en bout : le verdict voyage de la porte jusqu'au rapport ------


@pytest.mark.anyio
async def test_orchestrator_stamps_the_real_verdict_onto_the_order() -> None:
    """Chemin complet Council -> RiskGate -> broker.

    C'est le seul test qui prouve que la valeur inscrite dans le rapport vient
    bien du RiskEngine et non d'une constante recopiée par le broker.
    """
    from unittest.mock import AsyncMock, MagicMock

    from aegis_trade.application.paper_trading.orchestrator import (
        PaperTradingOrchestrator,
    )

    broker, repository = _paper_broker()
    risk_manager = GlobalRiskManager()
    portfolio = PortfolioEngine(initial_capital=10_000.0, risk_manager=risk_manager)

    orchestrator = PaperTradingOrchestrator(
        broker=broker,
        feed=MagicMock(),
        risk_manager=risk_manager,
        portfolio_engine=portfolio,
        event_publisher=AsyncMock(),
        council=MagicMock(),
        policy_store=MagicMock(),
        feature_provider=RollingFeatureProvider(
            extractor=TechnicalFeatureExtractor()
        ),
    )

    order_event = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        symbol=SYMBOL,
        action=OrderAction.BUY,
        volume=Decimal("1.0"),
        order_type="market",
        strategy_id="lot2b",
    )

    report = await orchestrator.submit_order(order_event, {SYMBOL: ASK})

    assert report.risk_decision == RISK_DECISION_APPROVED
    assert repository.saved[-1].risk_decision == RISK_DECISION_APPROVED


@pytest.mark.anyio
async def test_orchestrator_refused_order_never_reaches_the_broker() -> None:
    broker, repository = _paper_broker()
    risk_manager = GlobalRiskManager()
    risk_manager._emergency_halt_active = True
    portfolio = PortfolioEngine(initial_capital=10_000.0, risk_manager=risk_manager)

    from unittest.mock import AsyncMock, MagicMock

    from aegis_trade.application.paper_trading.orchestrator import (
        PaperTradingOrchestrator,
    )

    orchestrator = PaperTradingOrchestrator(
        broker=broker,
        feed=MagicMock(),
        risk_manager=risk_manager,
        portfolio_engine=portfolio,
        event_publisher=AsyncMock(),
        council=MagicMock(),
        policy_store=MagicMock(),
        feature_provider=RollingFeatureProvider(
            extractor=TechnicalFeatureExtractor()
        ),
    )

    order_event = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        symbol=SYMBOL,
        action=OrderAction.BUY,
        volume=Decimal("1.0"),
        order_type="market",
        strategy_id="lot2b",
    )

    with pytest.raises(OrderRejectedByRisk):
        await orchestrator.submit_order(order_event, {SYMBOL: ASK})

    assert repository.saved == []


def test_no_source_file_hardcodes_an_approval_string() -> None:
    """Garde-fou anti-régression sur la façade supprimée par ce lot.

    Un futur broker qui réintroduirait `risk_decision="APPROVED"` en dur
    passerait tous les tests fonctionnels ci-dessus tout en rétablissant
    exactement le mensonge que le lot 2B corrige.
    """
    import re
    from pathlib import Path

    src = Path(__file__).resolve().parents[3] / "src" / "aegis_trade"
    pattern = re.compile(r"""risk_decision\s*=\s*["']APPROVED["']""")

    offenders = [
        f"{path.relative_to(src)}:{number}"
        for path in src.rglob("*.py")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if pattern.search(line)
    ]

    assert offenders == [], f"Approbation codée en dur : {offenders}"

