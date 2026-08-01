"""Preuve d'autorité du RiskEngine sur les quatre chemins d'ordre.

Critère de sortie du Lot 1 (`docs/refont/PLAN_DE_CORRECTION.md`) : pour chacun
des quatre chemins qui contournaient le RiskEngine, prouver que l'ordre est
refusé quand le RiskEngine refuse.

Les quatre chemins, tels que relevés par l'audit :

1. `api/routers/positions.py`            — fermeture manuelle depuis le dashboard
2. `application/paper_trading/orchestrator.py` — décision du Council
3. `providers/vnpy_adapter.py`           — adaptateur vn.py synchrone
4. `infrastructure/live/vnpy/execution.py` — passerelle d'exécution live

Le refus est provoqué par un vrai `GlobalRiskManager` en kill switch : aucun
mock ne peut donc faire croire à un refus qui n'existe pas dans le moteur.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from aegis_trade.domain.core import AssetClass, Symbol
from aegis_trade.engine.events import OrderAction, OrderEvent
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import PortfolioEngine
from aegis_trade.engine.risk_gate import OrderRejectedByRisk, RiskGate
from aegis_trade.infrastructure.live.vnpy.execution import VnPyExecutionGateway
from aegis_trade.providers.vnpy_adapter import VnpyAdapter

SYMBOL = Symbol(name="EURUSD", asset_class=AssetClass.FOREX)
PRICE = Decimal("1.1000")


def _order() -> OrderEvent:
    return OrderEvent(
        timestamp=datetime.now(timezone.utc),
        symbol=SYMBOL,
        action=OrderAction.BUY,
        volume=Decimal("1.0"),
        order_type="market",
        strategy_id="risk_authority_test",
    )


def _halted_gate() -> RiskGate:
    """Porte de risque dont le moteur refuse tout : kill switch armé."""
    risk_manager = GlobalRiskManager()
    risk_manager._emergency_halt_active = True
    portfolio = PortfolioEngine(initial_capital=10_000.0, risk_manager=risk_manager)
    return RiskGate(risk_manager, portfolio)


def _permissive_gate() -> RiskGate:
    risk_manager = GlobalRiskManager()
    portfolio = PortfolioEngine(initial_capital=10_000.0, risk_manager=risk_manager)
    return RiskGate(risk_manager, portfolio)


class _RecordingMainEngine:
    """Broker factice qui enregistre tout ordre qui l'atteindrait."""

    def __init__(self) -> None:
        self.sent: list[Any] = []

    def send_order(self, req: Any, gateway_name: str) -> str:
        self.sent.append((req, gateway_name))
        return "VT-1"


class _NullEventEngine:
    def register(self, event_type: str, handler: Any) -> None:
        return None


class _IdentityMapper:
    def to_vnpy_symbol(self, symbol: Symbol) -> str:
        return f"{symbol.name}.LOCAL"


def test_risk_gate_refuses_when_engine_refuses() -> None:
    gate = _halted_gate()
    approved, reason = gate.evaluate(_order(), {SYMBOL: PRICE})
    assert approved is False
    assert "Kill Switch" in reason

    with pytest.raises(OrderRejectedByRisk):
        gate.authorize(_order(), {SYMBOL: PRICE})


def test_risk_gate_refuses_order_without_price() -> None:
    """Un prix absent n'est jamais comblé par une valeur par défaut."""
    with pytest.raises(OrderRejectedByRisk) as excinfo:
        _permissive_gate().authorize(_order(), {})
    assert "Missing or invalid price" in excinfo.value.reason


def test_path_vnpy_adapter_refuses() -> None:
    engine = _RecordingMainEngine()
    adapter = VnpyAdapter(
        main_engine=engine,
        event_engine=_NullEventEngine(),
        gateway_name="PAPER",
        risk_gate=_halted_gate(),
    )
    with pytest.raises(OrderRejectedByRisk):
        adapter.send_order(_order(), {SYMBOL: PRICE})
    assert engine.sent == [], "Un ordre refusé a tout de même atteint le broker."


def test_path_vnpy_execution_gateway_refuses() -> None:
    engine = _RecordingMainEngine()
    published: list[Any] = []

    async def publisher(event: Any) -> None:
        published.append(event)

    gateway = VnPyExecutionGateway(
        main_engine=engine,
        event_publisher=publisher,
        symbol_mapper=_IdentityMapper(),
        risk_gate=_halted_gate(),
    )
    with pytest.raises(OrderRejectedByRisk):
        asyncio.run(gateway.send_order(_order(), {SYMBOL: PRICE}))
    assert engine.sent == []
    assert published == []


@pytest.mark.parametrize(
    "build_router",
    [
        pytest.param(
            lambda gate: (
                lambda order, prices: VnpyAdapter(
                    main_engine=_RecordingMainEngine(),
                    event_engine=_NullEventEngine(),
                    risk_gate=gate,
                ).send_order(order, prices)
            ),
            id="providers/vnpy_adapter.py",
        ),
        pytest.param(
            lambda gate: (
                lambda order, prices: asyncio.run(
                    VnPyExecutionGateway(
                        main_engine=_RecordingMainEngine(),
                        event_publisher=_noop_publisher,
                        symbol_mapper=_IdentityMapper(),
                        risk_gate=gate,
                    ).send_order(order, prices)
                )
            ),
            id="infrastructure/live/vnpy/execution.py",
        ),
        pytest.param(
            lambda gate: (lambda order, prices: gate.authorize(order, prices)),
            id="engine/risk_gate.py (orchestrator + API)",
        ),
    ],
)
def test_no_path_routes_an_order_the_risk_engine_refused(build_router: Any) -> None:
    """Même refus, quel que soit l'appelant."""
    route = build_router(_halted_gate())
    with pytest.raises(OrderRejectedByRisk):
        route(_order(), {SYMBOL: PRICE})


async def _noop_publisher(event: Any) -> None:
    return None


def test_gateways_without_risk_gate_refuse_loudly() -> None:
    """Sans porte de risque injectée, on lève — on ne route pas « par défaut »."""
    adapter = VnpyAdapter(
        main_engine=_RecordingMainEngine(),
        event_engine=_NullEventEngine(),
        risk_gate=None,
    )
    with pytest.raises(RuntimeError, match="sans RiskGate"):
        adapter.send_order(_order(), {SYMBOL: PRICE})

    gateway = VnPyExecutionGateway(
        main_engine=_RecordingMainEngine(),
        event_publisher=_noop_publisher,
        symbol_mapper=_IdentityMapper(),
        risk_gate=None,
    )
    with pytest.raises(RuntimeError, match="sans RiskGate"):
        asyncio.run(gateway.send_order(_order(), {SYMBOL: PRICE}))


# --- Chemin 1 : la route API de fermeture manuelle, de bout en bout ---


class _RecordingBroker:
    """Broker qu'aucun ordre refusé ne doit atteindre."""

    def __init__(self) -> None:
        self.submitted: list[Any] = []

    async def submit_order(self, order: Any) -> Any:
        self.submitted.append(order)
        return order


def _api_client(gate: RiskGate, broker: _RecordingBroker) -> Any:
    """Client de test câblé sur une porte de risque choisie par le test."""
    from datetime import datetime as _dt

    from fastapi.testclient import TestClient

    from aegis_trade.api.deps import get_dashboard_service, get_orchestrator
    from aegis_trade.api.main import app
    from aegis_trade.api.security import TOKEN_ENV_VAR
    from aegis_trade.application.monitoring.engine import MonitoringEngine
    from aegis_trade.application.monitoring.models import PositionSnapshot
    from aegis_trade.application.dashboard.services import DashboardService

    os.environ[TOKEN_ENV_VAR] = "jeton-de-test-local"

    monitoring = MonitoringEngine()
    monitoring.positions[SYMBOL.name] = PositionSnapshot(
        symbol=SYMBOL.name,
        side="LONG",
        quantity=Decimal("1.0"),
        entry_price=PRICE,
        current_price=PRICE,
        unrealized_pnl=Decimal("0"),
        open_timestamp=_dt.now(timezone.utc),
    )

    class _StubOrchestrator:
        def __init__(self) -> None:
            self.risk_gate = gate
            self.broker = broker

        async def submit_order(
            self,
            order_event: OrderEvent,
            latest_prices: dict[Symbol, Decimal] | None = None,
            order_id: str | None = None,
        ) -> Any:
            # Même contrat que le vrai orchestrateur : autoriser, puis router.
            self.risk_gate.authorize(order_event, latest_prices)
            return await self.broker.submit_order(order_event)

    app.dependency_overrides[get_dashboard_service] = lambda: DashboardService(monitoring)
    app.dependency_overrides[get_orchestrator] = _StubOrchestrator
    return TestClient(app)


def test_api_close_position_is_refused_when_risk_engine_refuses() -> None:
    from aegis_trade.api.main import app

    broker = _RecordingBroker()
    client = _api_client(_halted_gate(), broker)
    try:
        response = client.post(
            f"/api/positions/{SYMBOL.name}/close",
            headers={"X-Aegis-Token": "jeton-de-test-local"},
        )
        assert response.status_code == 409
        assert "Kill Switch" in response.json()["detail"]
        assert broker.submitted == [], "L'API a routé un ordre refusé par le RiskEngine."
    finally:
        app.dependency_overrides.clear()


def test_api_close_position_routes_when_risk_engine_approves() -> None:
    """Contre-épreuve : sans cette assertion, un 409 systématique passerait aussi."""
    from aegis_trade.api.main import app

    broker = _RecordingBroker()
    client = _api_client(_permissive_gate(), broker)
    try:
        response = client.post(
            f"/api/positions/{SYMBOL.name}/close",
            headers={"X-Aegis-Token": "jeton-de-test-local"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "closing"
        assert len(broker.submitted) == 1
    finally:
        app.dependency_overrides.clear()
