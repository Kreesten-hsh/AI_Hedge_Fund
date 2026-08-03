"""Tests de la faisabilité économique d'un horizon.

L'invariant qui compte : le ratio est un PLAFOND atteignable par un oracle. S'il
vaut zéro, aucun modèle ne peut être rentable à cet horizon — c'est le résultat
qui a réfuté l'horizon 1 barre sur Crash 1000 (ADR 0019).
"""

import pytest

from aegis_trade.domain.costs import TransactionCostModel
from aegis_trade.domain.tradability import (
    absolute_moves,
    is_horizon_tradable,
    tradable_window_ratio,
)

COST = TransactionCostModel(commission_rate=0.001, slippage_bps=5.0)  # 30 bps A/R


class TestAbsoluteMoves:
    def test_moves_are_measured_over_the_full_holding_window(self) -> None:
        """Horizon 2 : on compare t+2 à t, pas deux fois t+1 à t."""
        moves = absolute_moves([100.0, 101.0, 102.0, 103.0], horizon=2)

        assert moves == pytest.approx([0.02, 0.019801980198])

    def test_direction_is_discarded(self) -> None:
        """Une baisse coûte le même péage qu'une hausse : seule l'amplitude compte."""
        up = absolute_moves([100.0, 110.0], horizon=1)
        down = absolute_moves([110.0, 100.0], horizon=1)

        assert up[0] == pytest.approx(0.10)
        assert down[0] == pytest.approx(0.0909090909)

    @pytest.mark.parametrize("horizon", [0, -1])
    def test_non_positive_horizon_is_refused(self, horizon: int) -> None:
        with pytest.raises(ValueError, match="horizon"):
            absolute_moves([100.0, 101.0], horizon=horizon)

    def test_series_too_short_for_the_horizon_is_refused(self) -> None:
        """Zéro fenêtre complète n'est pas un ratio de 0 : c'est une mesure impossible."""
        with pytest.raises(ValueError, match="aucune fenêtre complète"):
            absolute_moves([100.0, 101.0], horizon=5)

    def test_non_positive_price_is_refused(self) -> None:
        """Un prix nul rendrait le rendement indéfini et fausserait le ratio en silence."""
        with pytest.raises(ValueError, match="Prix non strictement positif"):
            absolute_moves([100.0, 0.0, 101.0], horizon=1)


class TestTradableWindowRatio:
    def test_a_market_that_never_covers_the_cost_scores_zero(self) -> None:
        """Le cas Crash 1000 à 1 barre : ~0.6 bps de mouvement, 30 bps de péage."""
        prices = [100.0 * (1.0 + (i % 2) * 0.00006) for i in range(50)]

        assert tradable_window_ratio(prices, horizon=1, cost_model=COST) == 0.0

    def test_a_market_that_always_covers_the_cost_scores_one(self) -> None:
        prices = [100.0 * (1.05**i) for i in range(20)]

        assert tradable_window_ratio(prices, horizon=1, cost_model=COST) == 1.0

    def test_the_ratio_counts_only_windows_at_or_above_the_threshold(self) -> None:
        # 3 fenêtres : +5 % (couvre), +0.01 % (ne couvre pas), +5 % (couvre).
        prices = [100.0, 105.0, 105.0105, 110.26]
        ratio = tradable_window_ratio(prices, horizon=1, cost_model=COST)

        assert ratio == pytest.approx(2.0 / 3.0)

    def test_a_longer_horizon_cannot_be_refuted_by_the_shortest_one(self) -> None:
        """Constat central de l'ADR 0019 : l'espace économique naît de la durée.

        Une dérive lente franchit le coût sur 10 barres et jamais sur 1. Le rejet
        d'un horizon ne dit donc rien des autres.
        """
        prices = [100.0 * (1.0005**i) for i in range(60)]

        assert tradable_window_ratio(prices, horizon=1, cost_model=COST) == 0.0
        assert tradable_window_ratio(prices, horizon=10, cost_model=COST) == 1.0

    def test_a_wider_safety_margin_can_only_lower_the_ratio(self) -> None:
        prices = [100.0 * (1.004**i) for i in range(30)]

        strict = tradable_window_ratio(prices, horizon=1, cost_model=COST)
        margined = tradable_window_ratio(
            prices, horizon=1, cost_model=COST, safety_margin=3.0
        )

        assert margined <= strict

    def test_a_cheaper_broker_can_only_raise_the_ratio(self) -> None:
        """Contre-épreuve du balayage de coût de l'ADR 0019."""
        prices = [100.0 * (1.0 + ((i % 3) * 0.0008)) for i in range(40)]
        cheap = TransactionCostModel(commission_rate=0.0, slippage_bps=1.0)

        assert tradable_window_ratio(prices, horizon=1, cost_model=cheap) >= (
            tradable_window_ratio(prices, horizon=1, cost_model=COST)
        )


class TestHorizonVerdict:
    def test_a_refuted_horizon_is_reported_as_untradable(self) -> None:
        prices = [100.0 * (1.0 + (i % 2) * 0.00006) for i in range(50)]

        assert is_horizon_tradable(prices, 1, COST, min_ratio=0.01) is False

    def test_an_horizon_meeting_the_ratio_is_reported_as_tradable(self) -> None:
        prices = [100.0 * (1.05**i) for i in range(20)]

        assert is_horizon_tradable(prices, 1, COST, min_ratio=0.50) is True

    @pytest.mark.parametrize("min_ratio", [0.0, -0.1, 1.5])
    def test_an_out_of_range_min_ratio_is_refused(self, min_ratio: float) -> None:
        """Un min_ratio de 0 rendrait tout horizon « tradable » par vacuité."""
        with pytest.raises(ValueError, match="min_ratio"):
            is_horizon_tradable([100.0, 101.0], 1, COST, min_ratio=min_ratio)
