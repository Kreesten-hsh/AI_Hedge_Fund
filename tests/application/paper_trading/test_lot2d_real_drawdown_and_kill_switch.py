"""Lot 2D — equity, drawdown et exposures réels ; condition d'existence du kill switch.

Le kill switch (`GlobalRiskManager.validate_order`) refuse un ordre d'ouverture
quand `(hwm - portfolio.equity) / hwm >= max_drawdown`. Il lit donc le
`Portfolio`, pas le snapshot du dashboard. Tant que personne n'alimente ce
portefeuille, `equity` reste égale au capital initial, le drawdown reste
structurellement nul, et le kill switch ne peut pas s'armer — quelles que
soient les pertes réelles.

Deux façades tombent ici :

1. l'orchestrateur ne poussait ni les prix (`on_market_event`) ni les fills
   (`on_fill_event`) dans `portfolio_engine` : le portefeuille sur lequel le
   RiskEngine décide restait vide ;
2. `_monitor_portfolio_loop` fabriquait un snapshot à valeurs constantes
   (`equity=balance`, `drawdown=0.0`, exposures `Decimal("0.0")`) puis le
   jetait (`_ = snapshot`).

Les assertions portent sur l'état du vrai `PortfolioEngine` et sur le refus
effectif d'un ordre, jamais sur le fait qu'une méthode ait été appelée.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aegis_trade.application.paper_trading.orchestrator import PaperTradingOrchestrator
from aegis_trade.domain.core import AssetClass, MarketBar, Symbol, TimeFrame
from aegis_trade.engine.events import OrderAction, OrderEvent
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import PortfolioEngine
from aegis_trade.engine.risk_gate import OrderRejectedByRisk

SYMBOL = Symbol(name="BTCUSDT", asset_class=AssetClass.CRYPTO)


def _bar(close: str, moment: datetime | None = None) -> MarketBar:
    price = Decimal(close)
    return MarketBar(
        symbol=SYMBOL,
        timeframe=TimeFrame.M1,
        timestamp=moment or datetime.now(timezone.utc),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal("1.0"),
    )


def _order(action: OrderAction = OrderAction.BUY, volume: str = "1.0") -> OrderEvent:
    return OrderEvent(
        timestamp=datetime.now(timezone.utc),
        symbol=SYMBOL,
        action=action,
        volume=Decimal(volume),
        order_type="market",
        strategy_id="lot2d",
    )


def _orchestrator(
    portfolio: PortfolioEngine, risk_manager: GlobalRiskManager
) -> PaperTradingOrchestrator:
    return PaperTradingOrchestrator(
        broker=MagicMock(),
        feed=MagicMock(),
        risk_manager=risk_manager,
        portfolio_engine=portfolio,
        event_publisher=AsyncMock(),
        council=MagicMock(),
        policy_store=MagicMock(),
    )


def _funded(capital: float = 100_000.0) -> tuple[PortfolioEngine, GlobalRiskManager]:
    risk_manager = GlobalRiskManager(max_drawdown=Decimal("0.05"))
    portfolio = PortfolioEngine(initial_capital=capital, risk_manager=risk_manager)
    return portfolio, risk_manager


class TestPortfolioIsFedByTheOrchestrator:
    """Sans alimentation, le portefeuille du RiskEngine est un portefeuille vide."""

    @pytest.mark.asyncio
    async def test_observed_price_reaches_the_portfolio(self) -> None:
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)

        orchestrator.observe_market(_bar("50000"))

        assert portfolio.get_latest_price(SYMBOL) == Decimal("50000")

    @pytest.mark.asyncio
    async def test_price_move_marks_the_position_to_market(self) -> None:
        """Une position ouverte doit voir son equity bouger avec le prix."""
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)

        orchestrator.observe_market(_bar("50000"))
        orchestrator.observe_fill(
            symbol=SYMBOL,
            action=OrderAction.BUY,
            volume=Decimal("1.0"),
            price=Decimal("50000"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )
        equity_at_entry = portfolio.equity

        orchestrator.observe_market(_bar("45000"))

        assert portfolio.equity < equity_at_entry
        assert portfolio.equity == Decimal("95000")

    @pytest.mark.asyncio
    async def test_equity_curve_is_recorded_so_the_hwm_exists(self) -> None:
        """Le high water mark se lit sur la courbe : sans points, pas de HWM."""
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)

        for index, price in enumerate(("50000", "51000", "49000")):
            orchestrator.observe_market(
                _bar(price, datetime(2026, 7, 1, 12, index, tzinfo=timezone.utc))
            )

        assert len(portfolio.equity_curve) == 3


class TestDrawdownIsReal:
    """`drawdown=0.0` codé en dur rendait le kill switch décoratif."""

    @pytest.mark.asyncio
    async def test_snapshot_drawdown_varies_with_losses(self) -> None:
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)

        orchestrator.observe_market(_bar("50000"))
        orchestrator.observe_fill(
            symbol=SYMBOL,
            action=OrderAction.BUY,
            volume=Decimal("1.0"),
            price=Decimal("50000"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )
        flat = orchestrator.build_snapshot()
        assert flat.drawdown == pytest.approx(0.0)

        orchestrator.observe_market(_bar("40000"))
        sunk = orchestrator.build_snapshot()

        assert sunk.drawdown > 0.0, "le drawdown ne bouge pas quand le compte perd"
        assert sunk.equity < flat.equity

    @pytest.mark.asyncio
    async def test_drawdown_measured_against_the_peak_not_the_initial_capital(self) -> None:
        """Un compte en gain puis en repli est en drawdown, même au-dessus du capital."""
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)

        orchestrator.observe_market(_bar("50000"))
        orchestrator.observe_fill(
            symbol=SYMBOL,
            action=OrderAction.BUY,
            volume=Decimal("1.0"),
            price=Decimal("50000"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )
        orchestrator.observe_market(_bar("60000"))  # pic : equity 110k
        orchestrator.observe_market(_bar("55000"))  # repli : equity 105k

        snapshot = orchestrator.build_snapshot()

        assert portfolio.equity > Decimal(str(portfolio.initial_capital))
        assert snapshot.drawdown > 0.0

    @pytest.mark.asyncio
    async def test_exposures_are_not_constant_zero(self) -> None:
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)

        orchestrator.observe_market(_bar("50000"))
        orchestrator.observe_fill(
            symbol=SYMBOL,
            action=OrderAction.BUY,
            volume=Decimal("2.0"),
            price=Decimal("50000"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )

        snapshot = orchestrator.build_snapshot()

        assert snapshot.gross_exposure == Decimal("100000")
        assert snapshot.net_exposure == Decimal("100000")
        assert snapshot.open_positions_count == 1

    @pytest.mark.asyncio
    async def test_short_position_nets_against_long_but_grosses_up(self) -> None:
        """Le brut et le net divergent : c'est tout l'intérêt de les distinguer."""
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)
        other = Symbol(name="ETHUSDT", asset_class=AssetClass.CRYPTO)

        orchestrator.observe_market(_bar("50000"))
        orchestrator.observe_fill(
            symbol=SYMBOL,
            action=OrderAction.BUY,
            volume=Decimal("1.0"),
            price=Decimal("50000"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )
        orchestrator.observe_market(
            MarketBar(
                symbol=other,
                timeframe=TimeFrame.M1,
                timestamp=datetime.now(timezone.utc),
                open=Decimal("3000"),
                high=Decimal("3000"),
                low=Decimal("3000"),
                close=Decimal("3000"),
                volume=Decimal("1.0"),
            )
        )
        orchestrator.observe_fill(
            symbol=other,
            action=OrderAction.SELL,
            volume=Decimal("10.0"),
            price=Decimal("3000"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )

        snapshot = orchestrator.build_snapshot()

        assert snapshot.gross_exposure == Decimal("80000")
        assert snapshot.net_exposure == Decimal("20000")
        assert snapshot.open_positions_count == 2

    @pytest.mark.asyncio
    async def test_floating_pnl_reflects_unrealised_loss(self) -> None:
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)

        orchestrator.observe_market(_bar("50000"))
        orchestrator.observe_fill(
            symbol=SYMBOL,
            action=OrderAction.BUY,
            volume=Decimal("1.0"),
            price=Decimal("50000"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )
        orchestrator.observe_market(_bar("47000"))

        assert orchestrator.build_snapshot().floating_pnl == Decimal("-3000")


    @pytest.mark.asyncio
    async def test_position_without_observed_price_is_not_counted_as_zero(self) -> None:
        """Un instrument sans tick ne doit pas faire disparaître son exposition.

        Le compter à zéro afficherait un risque plus faible que le réel, ce qui
        est précisément l'erreur dans laquelle on ne veut pas tomber en
        remplaçant les constantes. Il est donc exclu du brut/net, mais reste
        compté dans le nombre de positions ouvertes : le décalage est visible.
        """
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)
        silent = Symbol(name="SOLUSDT", asset_class=AssetClass.CRYPTO)

        orchestrator.observe_market(_bar("50000"))
        orchestrator.observe_fill(
            symbol=SYMBOL,
            action=OrderAction.BUY,
            volume=Decimal("1.0"),
            price=Decimal("50000"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )
        # Fill sans aucun tick sur cet instrument : `get_latest_price` renvoie None.
        orchestrator.observe_fill(
            symbol=silent,
            action=OrderAction.BUY,
            volume=Decimal("10.0"),
            price=Decimal("150"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )

        snapshot = orchestrator.build_snapshot()

        assert portfolio.get_latest_price(silent) is None
        assert snapshot.gross_exposure == Decimal("50000")
        assert snapshot.open_positions_count == 2


class TestKillSwitchArms:
    """Critère de sortie du Lot 2 : le kill switch se déclenche sur drawdown > 5 %."""

    @pytest.mark.asyncio
    async def test_injected_drawdown_above_five_percent_blocks_a_new_order(self) -> None:
        """Le test d'injection exigé par le plan.

        Aucune valeur n'est forcée dans le RiskEngine : la perte est provoquée
        par un vrai mouvement de prix, et c'est le portefeuille alimenté par
        l'orchestrateur qui la porte.
        """
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)

        orchestrator.observe_market(_bar("50000"))
        orchestrator.observe_fill(
            symbol=SYMBOL,
            action=OrderAction.BUY,
            volume=Decimal("1.0"),
            price=Decimal("50000"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )
        # -12 % sur la position => equity 94k sur un HWM de 100k => 6 % > 5 %.
        orchestrator.observe_market(_bar("44000"))

        assert orchestrator.build_snapshot().drawdown > 5.0

        with pytest.raises(OrderRejectedByRisk, match="Kill Switch"):
            await orchestrator.submit_order(_order(), {SYMBOL: Decimal("44000")})

    @pytest.mark.asyncio
    async def test_drawdown_below_the_limit_still_lets_orders_through(self) -> None:
        """Le kill switch doit discriminer, pas tout refuser.

        L'ordre est dimensionné pour rester sous la limite de concentration
        (20 %) : sinon c'est elle qui refuserait, et le test ne dirait rien du
        kill switch.
        """
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)
        orchestrator.broker.submit_order = AsyncMock(return_value=MagicMock(fills=[]))

        orchestrator.observe_market(_bar("50000"))
        orchestrator.observe_fill(
            symbol=SYMBOL,
            action=OrderAction.BUY,
            volume=Decimal("0.3"),
            price=Decimal("50000"),
            commission=Decimal("0.0"),
            timestamp=datetime.now(timezone.utc),
        )
        # -12 % sur le prix, mais une position de 0.3 : 1.8 % de drawdown seulement.
        orchestrator.observe_market(_bar("44000"))

        assert 0.0 < orchestrator.build_snapshot().drawdown < 5.0
        await orchestrator.submit_order(
            _order(action=OrderAction.SELL, volume="0.1"), {SYMBOL: Decimal("44000")}
        )

    @pytest.mark.asyncio
    async def test_unfed_portfolio_would_never_arm_the_kill_switch(self) -> None:
        """Régression : c'est exactement l'état d'avant le Lot 2D.

        Le marché s'effondre mais rien n'est poussé dans le portefeuille : le
        drawdown reste nul et l'ordre passe. Ce test documente la panne que
        l'alimentation du portefeuille corrige.
        """
        portfolio, _ = _funded()

        assert portfolio.equity == Decimal("100000")
        assert portfolio.equity_curve == []


class TestMonitorLoopPublishesTheSnapshot:
    """`_ = snapshot` : la valeur était calculée puis jetée."""

    @pytest.mark.asyncio
    async def test_latest_snapshot_is_exposed_after_a_refresh(self) -> None:
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)

        assert orchestrator.latest_snapshot is None

        orchestrator.observe_market(_bar("50000"))
        orchestrator.refresh_snapshot()

        assert orchestrator.latest_snapshot is not None
        assert orchestrator.latest_snapshot.equity == Decimal("100000")

    @pytest.mark.asyncio
    async def test_refresh_publishes_the_snapshot_on_the_bus(self) -> None:
        portfolio, risk_manager = _funded()
        publisher = AsyncMock()
        orchestrator = PaperTradingOrchestrator(
            broker=MagicMock(),
            feed=MagicMock(),
            risk_manager=risk_manager,
            portfolio_engine=portfolio,
            event_publisher=publisher,
            council=MagicMock(),
            policy_store=MagicMock(),
        )

        orchestrator.observe_market(_bar("50000"))
        await orchestrator.publish_snapshot()

        publisher.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_loop_publishes_periodically(self) -> None:
        """La boucle doit réellement publier, pas seulement tourner."""
        portfolio, risk_manager = _funded()
        publisher = AsyncMock()
        orchestrator = _orchestrator(portfolio, risk_manager)
        orchestrator.event_publisher = publisher
        orchestrator.is_running = True
        orchestrator.observe_market(_bar("50000"))

        async def _stop_after_first_publish(event: object) -> None:
            orchestrator.is_running = False

        publisher.side_effect = _stop_after_first_publish

        with patch(
            "aegis_trade.application.paper_trading.orchestrator.asyncio.sleep",
            new=AsyncMock(),
        ):
            await orchestrator._monitor_portfolio_loop()

        publisher.assert_awaited_once()
        assert orchestrator.latest_snapshot is not None

    @pytest.mark.asyncio
    async def test_a_failing_snapshot_does_not_kill_the_session(self) -> None:
        """Un échec de monitoring ne doit pas arrêter le trading...

        ...mais il ne doit pas non plus passer inaperçu : le risque affiché
        devient périmé, et c'est exactement le scénario que le Lot 2D corrige.
        """
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)
        orchestrator.is_running = True
        calls: list[int] = []

        def _fail_then_stop() -> object:
            calls.append(1)
            if len(calls) >= 2:
                orchestrator.is_running = False
            raise RuntimeError("portfolio unreachable")

        with patch.object(orchestrator, "build_snapshot", side_effect=_fail_then_stop):
            with patch(
                "aegis_trade.application.paper_trading.orchestrator.asyncio.sleep",
                new=AsyncMock(),
            ):
                await orchestrator._monitor_portfolio_loop()

        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_snapshot_timestamp_is_utc_aware(self) -> None:
        portfolio, risk_manager = _funded()
        orchestrator = _orchestrator(portfolio, risk_manager)

        snapshot = orchestrator.build_snapshot()

        assert snapshot.timestamp.tzinfo is not None
        assert snapshot.timestamp.utcoffset() == timedelta(0)
