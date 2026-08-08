"""Tests du barème de notation — la monotonie est la propriété sous test.

Un barème se prouve par ses invariants d'ordre, pas par des valeurs de score
codées en dur : une constante attendue se réajuste au premier changement de
pondération, un invariant d'ordre non.
"""

from typing import Dict, List, Optional

import pytest

from aegis_trade.domain.validation import (
    ValidationCampaignResult,
    ValidationCampaignType,
)
from aegis_trade.engine.scoring_engine import (
    MAX_TOLERATED_DRAWDOWN,
    ScoringEngine,
)


def _campaign(
    campaign_type: ValidationCampaignType,
    passed: bool,
    metrics: Optional[Dict[str, float]] = None,
) -> ValidationCampaignResult:
    return ValidationCampaignResult(
        campaign_type=campaign_type,
        metrics=metrics or {},
        passed=passed,
        details={},
    )


def _full_suite(
    net_return: float,
    drawdown: float = 0.0,
    ruin_probability: float = 0.0,
    all_passed: bool = True,
) -> List[ValidationCampaignResult]:
    """Les quatre campagnes du framework, paramétrées par le résultat économique."""
    return [
        _campaign(
            ValidationCampaignType.HOLD_OUT,
            all_passed,
            {"net_return": net_return, "max_drawdown": drawdown, "sharpe_ratio": 1.0},
        ),
        _campaign(
            ValidationCampaignType.WALK_FORWARD,
            all_passed,
            {"net_return": net_return, "max_drawdown": drawdown, "sharpe_ratio": 1.0},
        ),
        _campaign(
            ValidationCampaignType.MONTE_CARLO,
            all_passed,
            {"ruin_probability": ruin_probability, "median_net_return": net_return},
        ),
        _campaign(
            ValidationCampaignType.BENCHMARK,
            all_passed,
            {"alpha": net_return, "net_return": net_return},
        ),
    ]


@pytest.fixture
def engine() -> ScoringEngine:
    return ScoringEngine()


class TestMonotonicity:
    """Propriété centrale : à facteurs de risque constants, plus de PnL = plus de score."""

    @pytest.mark.parametrize(
        "lower,higher",
        [
            (-0.50, -0.37),
            (-0.37, -0.0102),
            (-0.0102, 0.0),
            (0.0, 0.001),
            (0.001, 0.05),
            (0.05, 0.20),
        ],
    )
    def test_score_strictly_increases_with_net_return(
        self, engine: ScoringEngine, lower: float, higher: float
    ) -> None:
        score_lower = engine.calculate_score(_full_suite(lower))
        score_higher = engine.calculate_score(_full_suite(higher))

        assert score_higher > score_lower, (
            f"net_return {higher} note {score_higher} <= {score_lower} pour {lower}"
        )

    def test_losing_strategy_never_outscores_a_winning_one(
        self, engine: ScoringEngine
    ) -> None:
        """Le défaut historique : une perte de -37 % notait 30, une perte de -1 % notait 0.

        On donne à la perdante tous les avantages de RISQUE (aucun drawdown,
        aucune ruine) et on les retire à la gagnante. La robustesse reste égale
        des deux côtés : c'est un portillon de preuve, pas un avantage
        échangeable contre du rendement (voir
        `test_a_winning_strategy_that_passes_nothing_still_scores_zero`).
        """
        loser = _full_suite(-0.3711, drawdown=0.0, ruin_probability=0.0, all_passed=True)
        winner = _full_suite(0.05, drawdown=0.10, ruin_probability=0.04, all_passed=True)

        assert engine.calculate_score(winner) > engine.calculate_score(loser)

    def test_a_winning_strategy_that_passes_nothing_still_scores_zero(
        self, engine: ScoringEngine
    ) -> None:
        """La robustesse est un portillon, pas un bonus qu'un gain peut compenser.

        Un rendement positif dont aucune campagne ne confirme la validité ne
        prouve rien : le facteur de robustesse à 0 annule le score. C'est
        l'asymétrie voulue — le rendement ordonne, les campagnes autorisent.
        """
        assert engine.calculate_score(_full_suite(0.05, all_passed=False)) == 0.0

    def test_zero_return_scores_at_midpoint_of_the_economic_term(
        self, engine: ScoringEngine
    ) -> None:
        """L'équilibre est le point neutre : ni crédité, ni puni économiquement."""
        score = engine.calculate_score(_full_suite(0.0))

        assert score == pytest.approx(50.0)


class TestHistoricalRegression:
    """Le cas exact qui a motivé la réécriture (`val_20260803_063600`)."""

    def _historical_campaigns(self) -> List[ValidationCampaignResult]:
        return [
            _campaign(
                ValidationCampaignType.HOLD_OUT,
                False,
                {"sharpe_ratio": -7.8977, "max_drawdown": 0.3702, "net_return": -0.3711},
            ),
            _campaign(
                ValidationCampaignType.WALK_FORWARD,
                False,
                {"sharpe_ratio": -7.9032, "win_rate": 0.0071, "net_return": -0.3711},
            ),
            _campaign(
                ValidationCampaignType.MONTE_CARLO,
                True,
                {"ruin_probability": 0.0},
            ),
            _campaign(
                ValidationCampaignType.BENCHMARK,
                False,
                {"alpha": -0.3784, "beta": -0.5646, "net_return": -0.3711},
            ),
        ]

    def test_the_minus_37_percent_run_now_scores_zero(
        self, engine: ScoringEngine
    ) -> None:
        """Ancien barème : 30/100. Un drawdown de 37 % dépasse la limite de 30 %."""
        score = engine.calculate_score(self._historical_campaigns())

        assert score == 0.0

    def test_monte_carlo_pass_alone_cannot_lift_a_losing_run(
        self, engine: ScoringEngine
    ) -> None:
        """L'ancien bonus binaire de +20 points n'existe plus.

        Même en supprimant la pénalité de drawdown, un PASS Monte-Carlo isolé
        sur une stratégie à -37 % doit rester très en dessous du seuil
        d'approbation de 75.
        """
        campaigns = [
            _campaign(
                ValidationCampaignType.HOLD_OUT,
                False,
                {"net_return": -0.3711, "max_drawdown": 0.0},
            ),
            _campaign(
                ValidationCampaignType.MONTE_CARLO, True, {"ruin_probability": 0.0}
            ),
        ]

        assert engine.calculate_score(campaigns) < 5.0


class TestRiskFactors:
    """Les facteurs de risque ne peuvent que retirer des points, jamais en ajouter."""

    def test_drawdown_penalty_is_continuous_not_binary(
        self, engine: ScoringEngine
    ) -> None:
        scores = [
            engine.calculate_score(_full_suite(0.05, drawdown=dd))
            for dd in (0.0, 0.05, 0.10, 0.20)
        ]

        assert scores == sorted(scores, reverse=True)
        assert len(set(scores)) == len(scores), "pénalité par palier, pas continue"

    def test_drawdown_beyond_the_risk_limit_zeroes_the_score(
        self, engine: ScoringEngine
    ) -> None:
        """Au-delà de la limite de risque, aucun rendement ne rachète la stratégie."""
        score = engine.calculate_score(
            _full_suite(0.50, drawdown=MAX_TOLERATED_DRAWDOWN + 0.01)
        )

        assert score == 0.0

    def test_low_ruin_probability_grants_no_bonus(self, engine: ScoringEngine) -> None:
        """P(ruine)=0 est un prérequis, pas une performance : facteur plafonné à 1."""
        no_ruin = engine.calculate_score(_full_suite(0.05, ruin_probability=0.0))
        some_ruin = engine.calculate_score(_full_suite(0.05, ruin_probability=0.30))

        assert no_ruin > some_ruin
        assert no_ruin <= 100.0

    def test_ruin_probability_scales_the_score_down_proportionally(
        self, engine: ScoringEngine
    ) -> None:
        baseline = engine.calculate_score(_full_suite(0.05, ruin_probability=0.0))
        halved = engine.calculate_score(_full_suite(0.05, ruin_probability=0.50))

        assert halved == pytest.approx(baseline * 0.5)


class TestFalsifiability:
    """Retirer une campagne gênante ne doit jamais améliorer le score."""

    def test_dropping_a_failing_campaign_does_not_raise_the_score(
        self, engine: ScoringEngine
    ) -> None:
        with_failure = _full_suite(0.05, all_passed=True)
        with_failure[1] = _campaign(
            ValidationCampaignType.WALK_FORWARD,
            False,
            {"net_return": 0.05, "max_drawdown": 0.0},
        )
        without_campaign = [c for c in with_failure if c.campaign_type != ValidationCampaignType.WALK_FORWARD]

        assert engine.calculate_score(without_campaign) <= engine.calculate_score(
            with_failure
        )

    def test_full_suite_passed_is_required_to_reach_the_approval_threshold(
        self, engine: ScoringEngine
    ) -> None:
        """Le seuil d'approbation (75) est inatteignable si une campagne échoue."""
        partial = _full_suite(0.50, all_passed=True)
        partial[0] = _campaign(
            ValidationCampaignType.HOLD_OUT,
            False,
            {"net_return": 0.50, "max_drawdown": 0.0},
        )

        assert engine.calculate_score(partial) < 75.0

    def test_an_excellent_strategy_can_still_be_approved(
        self, engine: ScoringEngine
    ) -> None:
        """Un barème qui ne peut jamais approuver n'est pas un barème, c'est un mur."""
        score = engine.calculate_score(
            _full_suite(0.20, drawdown=0.02, ruin_probability=0.0, all_passed=True)
        )

        assert score >= 75.0


class TestDegenerateInputs:
    def test_no_campaign_scores_zero(self, engine: ScoringEngine) -> None:
        assert engine.calculate_score([]) == 0.0

    def test_missing_net_return_scores_zero_not_neutral(
        self, engine: ScoringEngine
    ) -> None:
        """Non mesuré n'est pas neutre : sans PnL observé, rien n'est notable."""
        campaigns = [
            _campaign(ValidationCampaignType.HOLD_OUT, True, {"sharpe_ratio": 3.0}),
            _campaign(ValidationCampaignType.MONTE_CARLO, True, {"ruin_probability": 0.0}),
        ]

        assert engine.calculate_score(campaigns) == 0.0

    def test_score_stays_within_bounds_on_extreme_returns(
        self, engine: ScoringEngine
    ) -> None:
        assert 0.0 <= engine.calculate_score(_full_suite(1000.0)) <= 100.0
        assert 0.0 <= engine.calculate_score(_full_suite(-0.99)) <= 100.0
