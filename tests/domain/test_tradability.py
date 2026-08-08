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
    max_viable_round_trip_cost,
    oracle_holding_periods,
    oracle_target_exposure,
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


class TestMaxViableRoundTripCost:
    """Borne de coût indépendante de toute hypothèse de frais.

    Motivation mesurée : le catalogue d'offres Deriv est vide depuis cet
    environnement, donc le spread réel de Crash 1000 n'est pas lisible par API.
    Choisir l'horizon cible à partir des 30 bps du `SimulatedBroker` reviendrait
    à bâtir la recherche sur un chiffre non mesuré. Cette borne renverse la
    question et ne dépend d'aucun coût.
    """

    # Mouvements tous distincts et jamais nuls (7 est premier avec 13, donc les
    # résidus consécutifs ne se répètent pas) : la borne est isolable sans que
    # des ex aequo au point de coupure rendent le test ambigu.
    PRICES = [100.0 * (1.0 + 0.001 * ((i * 7) % 13)) for i in range(60)]

    @staticmethod
    def _cost_of(round_trip: float) -> TransactionCostModel:
        """Modèle dont l'aller-retour vaut exactement `round_trip`."""
        return TransactionCostModel(commission_rate=round_trip / 2.0, slippage_bps=0.0)

    @pytest.mark.parametrize("min_ratio", [0.05, 0.2, 0.5, 1.0])
    def test_the_bound_delivers_the_ratio_it_promises(self, min_ratio: float) -> None:
        """Inversion : le coût rendu tient bien la part de fenêtres exigée."""
        bound = max_viable_round_trip_cost(self.PRICES, horizon=1, min_ratio=min_ratio)

        ratio = tradable_window_ratio(self.PRICES, 1, self._cost_of(bound))

        assert ratio >= min_ratio

    @pytest.mark.parametrize("min_ratio", [0.05, 0.2, 0.5])
    def test_a_cost_above_the_bound_breaks_the_promise(self, min_ratio: float) -> None:
        """La borne est serrée, pas seulement suffisante.

        Sans cette contre-épreuve, retourner zéro passerait le test d'inversion
        tout en étant inutile.
        """
        bound = max_viable_round_trip_cost(self.PRICES, horizon=1, min_ratio=min_ratio)

        ratio = tradable_window_ratio(self.PRICES, 1, self._cost_of(bound * 1.000001))

        assert ratio < min_ratio

    def test_demanding_every_window_selects_the_smallest_move(self) -> None:
        """À 100 % de fenêtres, seul le mouvement le plus faible est finançable."""
        moves = absolute_moves(self.PRICES, horizon=1)

        bound = max_viable_round_trip_cost(self.PRICES, horizon=1, min_ratio=1.0)

        assert bound == pytest.approx(min(moves))

    def test_demanding_more_windows_lowers_the_affordable_cost(self) -> None:
        """Monotonie : exiger plus d'occasions ne peut pas relâcher la contrainte."""
        lenient = max_viable_round_trip_cost(self.PRICES, horizon=1, min_ratio=0.10)
        strict = max_viable_round_trip_cost(self.PRICES, horizon=1, min_ratio=0.90)

        assert strict <= lenient

    def test_a_longer_horizon_affords_a_higher_cost(self) -> None:
        """Le fait qui rouvre l'hypothèse de l'ADR 0019 : tenir plus longtemps paie."""
        prices = [100.0 * (1.0005**i) for i in range(60)]

        short = max_viable_round_trip_cost(prices, horizon=1, min_ratio=0.5)
        long = max_viable_round_trip_cost(prices, horizon=30, min_ratio=0.5)

        assert long > short

    @pytest.mark.parametrize("min_ratio", [0.0, -0.1, 1.5])
    def test_an_out_of_range_min_ratio_is_refused(self, min_ratio: float) -> None:
        with pytest.raises(ValueError, match="min_ratio"):
            max_viable_round_trip_cost(self.PRICES, 1, min_ratio=min_ratio)


class TestOracleTargetExposure:
    """L'exposition qu'une `MLStrategy` déclarerait si elle prédisait parfaitement.

    La règle reproduite est celle de `MLStrategy.generate_signals` :
    `>= +seuil` long, `<= -seuil` short, entre les deux PLAT — la zone morte est
    un ordre de sortie, pas un silence. Reproduire la règle exacte est ce qui
    fait de cette mesure une réponse à la question de SIG-02 plutôt qu'une
    statistique de persistance générique.
    """

    def test_the_dead_zone_is_reported_as_flat(self) -> None:
        """Sous le coût d'un aller-retour, l'oracle lui-même reste plat."""
        prices = [100.0, 100.5, 100.0, 100.0, 99.6, 99.6]

        exposure = oracle_target_exposure(prices, horizon=1, cost_model=COST)

        assert exposure == [1, -1, 0, -1, 0]

    def test_one_exposure_per_complete_window(self) -> None:
        """Les `horizon` dernières barres n'ont pas de rendement futur : pas d'avis."""
        prices = [100.0 * (1.01**i) for i in range(20)]

        assert len(oracle_target_exposure(prices, horizon=5, cost_model=COST)) == 15

    def test_a_move_just_under_the_threshold_stays_flat(self) -> None:
        """Contre-épreuve du seuil : la frontière n'est pas franchie par arrondi."""
        threshold = COST.breakeven_return()
        prices = [100.0, 100.0 * (1.0 + threshold * 0.999)]

        assert oracle_target_exposure(prices, horizon=1, cost_model=COST) == [0]

    def test_the_sign_of_the_move_sets_the_side(self) -> None:
        """Un mouvement en fraction du prix est asymétrique : les deux sens comptent."""
        up = oracle_target_exposure([100.0, 110.0], horizon=1, cost_model=COST)
        down = oracle_target_exposure([110.0, 100.0], horizon=1, cost_model=COST)

        assert up == [1]
        assert down == [-1]

    @pytest.mark.parametrize("horizon", [0, -1])
    def test_non_positive_horizon_is_refused(self, horizon: int) -> None:
        with pytest.raises(ValueError, match="horizon"):
            oracle_target_exposure([100.0, 101.0], horizon, COST)

    def test_series_too_short_for_the_horizon_is_refused(self) -> None:
        with pytest.raises(ValueError, match="aucune fenêtre complète"):
            oracle_target_exposure([100.0, 101.0], 5, COST)

    def test_non_positive_price_is_refused(self) -> None:
        with pytest.raises(ValueError, match="Prix non strictement positif"):
            oracle_target_exposure([100.0, 0.0, 101.0], 1, COST)


class TestOracleHoldingPeriods:
    """Durée de détention effective d'une sortie par persistance du signal.

    La question ouverte de SIG-02 : le gate de tradabilité mesure une sortie
    TEMPORELLE (`absolute_moves` compare `t+horizon` à `t`), alors que
    `MLStrategy` sort quand le signal se dégrade. Ces deux durées ne coïncident
    pas par construction. Si la détention médiane tombe à 1 barre alors que le
    label porte sur 5, la stratégie paie un aller-retour dimensionné sur un
    mouvement de 5 barres pour capter un mouvement d'une barre — l'horizon
    1 barre réfuté par l'ADR 0019, réintroduit par la porte de sortie.
    """

    def test_a_persistent_signal_yields_a_single_holding(self) -> None:
        """Détention >> horizon : un seul péage payé sur toute la tendance."""
        prices = [100.0 * (1.01**i) for i in range(20)]

        assert oracle_holding_periods(prices, horizon=1, cost_model=COST) == [19]

    def test_a_sign_flip_closes_the_holding(self) -> None:
        """Passer long à short est un aller-retour, pas une détention continue."""
        prices = [100.0, 100.5, 100.0, 100.5]

        periods = oracle_holding_periods(prices, horizon=1, cost_model=COST)

        assert periods == [1, 1, 1]

    def test_a_flat_bar_closes_the_holding(self) -> None:
        """La zone morte ordonne la sortie : elle scinde la détention en deux."""
        prices = [100.0, 100.5, 101.0, 101.0, 101.5]

        periods = oracle_holding_periods(prices, horizon=1, cost_model=COST)

        assert periods == [2, 1]

    def test_a_market_that_never_covers_the_cost_never_holds(self) -> None:
        """Zéro détention n'est pas une détention de zéro barre : la liste est vide."""
        prices = [100.0 * (1.0 + (i % 2) * 0.00006) for i in range(50)]

        assert oracle_holding_periods(prices, horizon=1, cost_model=COST) == []

    def test_holding_bars_reconcile_with_the_tradable_window_ratio(self) -> None:
        """Le pont entre la nouvelle mesure et le gate existant.

        Une barre est détenue exactement quand sa fenêtre couvre le péage. La
        somme des détentions doit donc redonner le numérateur du ratio. Sans cet
        invariant, les deux mesures pourraient dériver l'une de l'autre en
        silence et le diagnostic de SIG-02 ne prouverait plus rien sur le gate.
        """
        prices = [100.0 * (1.0 + 0.004 * ((i * 7) % 13)) for i in range(60)]
        horizon = 3

        periods = oracle_holding_periods(prices, horizon, COST)
        ratio = tradable_window_ratio(prices, horizon, COST)
        windows = len(absolute_moves(prices, horizon))

        assert sum(periods) == pytest.approx(ratio * windows)

    def test_a_wider_safety_margin_cannot_increase_time_in_position(self) -> None:
        """Monotonie : exiger plus de marge ne peut que retirer des barres détenues.

        Le nombre de détentions peut monter (une marge plus haute scinde un run),
        mais le temps total exposé, jamais.
        """
        prices = [100.0 * (1.0 + 0.004 * ((i * 7) % 13)) for i in range(60)]

        strict = oracle_holding_periods(prices, 3, COST, safety_margin=1.0)
        margined = oracle_holding_periods(prices, 3, COST, safety_margin=3.0)

        assert sum(margined) <= sum(strict)

    @pytest.mark.parametrize("horizon", [0, -1])
    def test_non_positive_horizon_is_refused(self, horizon: int) -> None:
        with pytest.raises(ValueError, match="horizon"):
            oracle_holding_periods([100.0, 101.0], horizon, COST)
