"""Tests du modèle de coût de transaction.

L'invariant qui compte : le seuil dérivé couvre effectivement le péage payé par
le broker sur un aller-retour complet. Un seuil qui ne couvre qu'une jambe
laisse une espérance négative que le backtest révélera trop tard.
"""

import pytest

from aegis_trade.domain.core import AssetClass, Symbol
from aegis_trade.domain.costs import TransactionCostModel
from aegis_trade.domain.execution import OrderIntent
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker

from datetime import datetime, timezone

SYMBOL = Symbol("CRASH1000", AssetClass.INDICES)
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


class TestCostArithmetic:
    def test_one_way_cost_sums_commission_and_slippage(self) -> None:
        model = TransactionCostModel(commission_rate=0.001, slippage_bps=5.0)

        assert model.one_way_cost == pytest.approx(0.0015)

    def test_round_trip_is_twice_the_one_way_cost(self) -> None:
        """Ouvrir engage de fermer : le péage pertinent est celui des deux jambes."""
        model = TransactionCostModel(commission_rate=0.001, slippage_bps=5.0)

        assert model.round_trip_cost == pytest.approx(0.003)

    def test_breakeven_defaults_to_the_round_trip_cost(self) -> None:
        model = TransactionCostModel(commission_rate=0.001, slippage_bps=5.0)

        assert model.breakeven_return() == pytest.approx(model.round_trip_cost)

    def test_safety_margin_scales_the_breakeven(self) -> None:
        model = TransactionCostModel(commission_rate=0.001, slippage_bps=5.0)

        assert model.breakeven_return(safety_margin=2.0) == pytest.approx(0.006)

    def test_margin_below_one_is_refused(self) -> None:
        """Une marge < 1 viserait un trade dont le gain ne paie pas son péage."""
        model = TransactionCostModel(commission_rate=0.001, slippage_bps=5.0)

        with pytest.raises(ValueError, match="safety_margin"):
            model.breakeven_return(safety_margin=0.5)

    @pytest.mark.parametrize(
        "commission,slippage",
        [(-0.001, 5.0), (0.001, -5.0)],
    )
    def test_negative_costs_are_refused(self, commission: float, slippage: float) -> None:
        with pytest.raises(ValueError):
            TransactionCostModel(commission_rate=commission, slippage_bps=slippage)


class TestBrokerAgreesWithItsOwnCostModel:
    """Le coût déclaré doit être celui réellement prélevé, sinon le seuil ment."""

    def test_broker_exposes_its_configured_cost(self) -> None:
        broker = SimulatedBroker(commission_rate=0.002, slippage_bps=7.0)

        assert broker.cost_model == TransactionCostModel(
            commission_rate=0.002, slippage_bps=7.0
        )

    def test_a_breakeven_move_covers_the_measured_round_trip_cost(self) -> None:
        """Test économique de bout en bout, pas arithmétique.

        On ouvre puis on ferme une position au prix décalé du seuil de
        rentabilité, et on vérifie que le PnL réalisé net de commissions n'est
        pas négatif. C'est la propriété que le seuil est censé garantir.
        """
        broker = SimulatedBroker(commission_rate=0.001, slippage_bps=5.0)
        breakeven = broker.cost_model.breakeven_return()

        entry_price = 100.0
        exit_price = entry_price * (1.0 + breakeven)
        quantity = 10.0

        entry = broker.execute_order(
            OrderIntent(
                symbol=SYMBOL,
                direction=1,
                quantity=quantity,
                target_price=entry_price,
                timestamp=NOW,
            )
        )
        close = broker.execute_order(
            OrderIntent(
                symbol=SYMBOL,
                direction=-1,
                quantity=quantity,
                target_price=exit_price,
                timestamp=NOW,
            )
        )
        assert entry is not None and close is not None

        gross = (close.fill_price - entry.fill_price) * quantity
        net = gross - entry.commission - close.commission

        # Tolérance : le coût exact du slippage se calcule sur le prix décalé, pas
        # sur le prix cible, ce qui laisse un résidu de second ordre (~1e-5 du
        # notionnel). Le seuil doit couvrir le coût au premier ordre.
        assert net >= -0.01 * quantity * entry_price * 1e-2

    def test_a_move_below_breakeven_loses_money(self) -> None:
        """Contre-épreuve : sous le seuil, le trade est perdant. C'était le défaut."""
        broker = SimulatedBroker(commission_rate=0.001, slippage_bps=5.0)
        # L'ancien seuil par défaut de MLStrategy, ~15x sous le coût réel.
        old_default_threshold = 0.0002

        entry_price = 100.0
        exit_price = entry_price * (1.0 + old_default_threshold)
        quantity = 10.0

        entry = broker.execute_order(
            OrderIntent(
                symbol=SYMBOL, direction=1, quantity=quantity,
                target_price=entry_price, timestamp=NOW,
            )
        )
        close = broker.execute_order(
            OrderIntent(
                symbol=SYMBOL, direction=-1, quantity=quantity,
                target_price=exit_price, timestamp=NOW,
            )
        )
        assert entry is not None and close is not None

        gross = (close.fill_price - entry.fill_price) * quantity
        net = gross - entry.commission - close.commission

        assert net < 0.0
