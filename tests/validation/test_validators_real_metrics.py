import pytest
from datetime import datetime, timezone, timedelta
from typing import List
from unittest.mock import Mock

from aegis_trade.domain.core import Symbol, TimeFrame, AssetClass
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.validation import ValidationCampaignType
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validators.hold_out_validator import HoldOutValidator
from aegis_trade.application.validation.validators.walk_forward_validator import WalkForwardValidator
from aegis_trade.application.validation.validators.monte_carlo_validator import MonteCarloValidator
from aegis_trade.application.validation.validators.benchmark_validator import BenchmarkValidator
from aegis_trade.application.validation.validators.multi_validators import MultiMarketValidator, MultiTimeframeValidator
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker

class LosingStrategy(IStrategy):
    """Stratégie qui vend à découvert sur une forte hausse (génère des pertes)."""
    def __init__(self):
        self._sold = False

    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        if not self._sold:
            self._sold = True
            return [
                Signal(
                    symbol=features.symbol,
                    direction=-1,  # Short sur marché haussier
                    strength=1.0,
                    timestamp=features.timestamp
                )
            ]
        return []

class WinningStrategy(IStrategy):
    """Stratégie tendance qui achète au début d'une hausse."""
    def __init__(self):
        self._bought = False

    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        if not self._bought:
            self._bought = True
            return [
                Signal(
                    symbol=features.symbol,
                    direction=1,  # Long sur marché haussier
                    strength=1.0,
                    timestamp=features.timestamp
                )
            ]
        return []

class InertStrategy(IStrategy):
    """Stratégie inerte qui ne génère aucun ordre (0 trade)."""
    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        return []

class ChurningStrategy(IStrategy):
    """Stratégie qui inverse sa position à chaque barre.

    Seul moyen d'obtenir un échantillon de trades au-dessus du plancher du
    bootstrap Monte-Carlo : les stratégies `Losing`/`Winning` n'entrent qu'une
    fois et laissent 1 seul trade dans l'historique.
    """
    def __init__(self):
        self._direction = 1

    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        self._direction = -self._direction
        return [
            Signal(
                symbol=features.symbol,
                direction=self._direction,
                strength=1.0,
                timestamp=features.timestamp
            )
        ]

@pytest.fixture
def uptrend_data_feed():
    mock_feed = Mock()
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    # Tendance haussière continue sur 30 barres
    bars = [
        FeatureSet(
            symbol=Symbol("CRASH1000", AssetClass.INDICES),
            timeframe=TimeFrame.M1,
            timestamp=now + timedelta(minutes=i),
            features={"close_price": 100.0 + (i * 2.0), "close": 100.0 + (i * 2.0)}
        )
        for i in range(30)
    ]
    mock_feed.get_feature_stream.side_effect = lambda symbol, timeframe: iter(bars)
    return mock_feed

@pytest.fixture
def long_uptrend_data_feed():
    """80 barres : assez pour dépasser le plancher d'échantillon du bootstrap."""
    mock_feed = Mock()
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    bars = [
        FeatureSet(
            symbol=Symbol("CRASH1000", AssetClass.INDICES),
            timeframe=TimeFrame.M1,
            timestamp=now + timedelta(minutes=i),
            features={"close_price": 100.0 + (i * 2.0), "close": 100.0 + (i * 2.0)}
        )
        for i in range(80)
    ]
    mock_feed.get_feature_stream.side_effect = lambda symbol, timeframe: iter(bars)
    return mock_feed

def test_inert_strategy_fails_monte_carlo(uptrend_data_feed):
    config = ValidationConfig(
        active_campaigns=[ValidationCampaignType.MONTE_CARLO],
        markets=[Symbol("CRASH1000", AssetClass.INDICES)],
        timeframes=[TimeFrame.M1]
    )
    inert_strat = InertStrategy()

    res_mc = MonteCarloValidator().run(inert_strat, uptrend_data_feed, SimulatedBroker, config)
    # Une stratégie inerte (0 trade) DOIT échouer (passed=False)
    assert res_mc.passed is False
    assert res_mc.metrics["ruin_probability"] == 1.0

def test_undersized_sample_fails_monte_carlo_as_non_conclusive(uptrend_data_feed):
    """Sous le plancher d'échantillon, le bootstrap ne mesure rien : échec non concluant.

    Avant le plancher, une stratégie à 1 seul trade « passait » Monte-Carlo avec
    P(ruine)=0.0 — creux statistique qui remontait le score global. Un résultat
    non concluant doit échouer, pas passer par défaut.
    """
    config = ValidationConfig(
        active_campaigns=[ValidationCampaignType.MONTE_CARLO],
        markets=[Symbol("CRASH1000", AssetClass.INDICES)],
        timeframes=[TimeFrame.M1]
    )
    res_mc = MonteCarloValidator().run(LosingStrategy(), uptrend_data_feed, SimulatedBroker, config)

    assert res_mc.passed is False
    assert res_mc.metrics["ruin_probability"] == 1.0
    assert res_mc.details["trades_count"] < res_mc.details["min_trades_required"]
    assert "non concluant" in res_mc.details["reason"]

def test_sufficient_sample_runs_the_real_bootstrap(long_uptrend_data_feed):
    """Au-dessus du plancher, le bootstrap tourne vraiment et mesure P(ruine).

    Contre-épreuve du test précédent : le plancher ne doit pas court-circuiter
    toute campagne Monte-Carlo, seulement les échantillons non concluants.
    """
    config = ValidationConfig(
        active_campaigns=[ValidationCampaignType.MONTE_CARLO],
        markets=[Symbol("CRASH1000", AssetClass.INDICES)],
        timeframes=[TimeFrame.M1]
    )
    res_mc = MonteCarloValidator().run(
        ChurningStrategy(), long_uptrend_data_feed, SimulatedBroker, config
    )

    assert res_mc.details["trades_sampled"] >= res_mc.details["min_trades_required"]
    # Bootstrap réellement exécuté : la borne d'itérations est appliquée et
    # P(ruine) est une probabilité mesurée, pas la valeur sentinelle 1.0 du rejet.
    assert res_mc.details["iterations"] == 1000
    assert 0.0 <= res_mc.metrics["ruin_probability"] <= 1.0
    # PASS exige désormais de gagner de l'argent dans le cas central, pas
    # seulement d'éviter la ruine (ADR 0017) : P(ruine)=0 était compatible avec
    # une perte systématique de 37 %, et créditait quand même la campagne.
    assert res_mc.passed is (
        res_mc.metrics["ruin_probability"] < 0.05
        and res_mc.metrics["median_net_return"] > 0.0
    )

def test_monte_carlo_exposes_the_real_loss_not_only_ruin(long_uptrend_data_feed):
    """La ruine ne mesure que la queue à -50 % : la perte centrale doit être exposée.

    Sans ces métriques, une stratégie perdant systématiquement sous le seuil de
    ruine affichait P(ruine)=0.0 et rien d'autre — aucune trace chiffrée de la
    perte réelle sur laquelle le barème puisse s'appuyer.
    """
    config = ValidationConfig(
        active_campaigns=[ValidationCampaignType.MONTE_CARLO],
        markets=[Symbol("CRASH1000", AssetClass.INDICES)],
        timeframes=[TimeFrame.M1]
    )
    res_mc = MonteCarloValidator().run(
        ChurningStrategy(), long_uptrend_data_feed, SimulatedBroker, config
    )

    assert 0.0 <= res_mc.metrics["loss_probability"] <= 1.0
    # La queue basse ne peut pas être meilleure que le cas central.
    assert res_mc.metrics["expected_shortfall"] <= res_mc.metrics["median_net_return"]

def test_holdout_and_walk_forward_expose_net_return(uptrend_data_feed):
    """Le barème note le PnL net réel : les campagnes doivent le rapporter.

    Un `net_return` absent vaut score nul (non mesuré n'est pas neutre), donc son
    exposition par les validateurs hors-échantillon est structurelle, pas
    cosmétique.
    """
    config = ValidationConfig(
        active_campaigns=[ValidationCampaignType.HOLD_OUT, ValidationCampaignType.WALK_FORWARD],
        markets=[Symbol("CRASH1000", AssetClass.INDICES)],
        timeframes=[TimeFrame.M1]
    )

    res_ho = HoldOutValidator().run(WinningStrategy(), uptrend_data_feed, SimulatedBroker, config)
    res_wf = WalkForwardValidator().run(WinningStrategy(), uptrend_data_feed, SimulatedBroker, config)

    assert "net_return" in res_ho.metrics
    assert "net_return" in res_wf.metrics
    assert "max_drawdown" in res_wf.metrics
    # Long sur tendance haussière : le rendement net doit être positif.
    assert res_ho.metrics["net_return"] > 0.0

def test_walk_forward_compounds_fold_returns(uptrend_data_feed):
    """Rendement composé, pas moyenné : un fold à -50 % ne s'annule pas avec +50 %."""
    config = ValidationConfig(
        active_campaigns=[ValidationCampaignType.WALK_FORWARD],
        markets=[Symbol("CRASH1000", AssetClass.INDICES)],
        timeframes=[TimeFrame.M1]
    )
    res_wf = WalkForwardValidator().run(WinningStrategy(), uptrend_data_feed, SimulatedBroker, config)

    expected = 1.0
    for fold_return in res_wf.details["fold_returns"]:
        expected *= (1.0 + fold_return)

    assert res_wf.metrics["net_return"] == pytest.approx(expected - 1.0, abs=1e-6)

def test_losing_strategy_fails_benchmark_and_holdout(uptrend_data_feed):
    config = ValidationConfig(
        active_campaigns=[ValidationCampaignType.HOLD_OUT, ValidationCampaignType.BENCHMARK],
        markets=[Symbol("CRASH1000", AssetClass.INDICES)],
        timeframes=[TimeFrame.M1]
    )
    
    res_ho = HoldOutValidator().run(LosingStrategy(), uptrend_data_feed, SimulatedBroker, config)
    res_bm = BenchmarkValidator().run(LosingStrategy(), uptrend_data_feed, SimulatedBroker, config)
    
    # Une stratégie perdante DOIT échouer aux deux tests
    assert res_ho.passed is False
    assert res_bm.passed is False
    assert res_bm.metrics["alpha"] < 0.0

def test_winning_strategy_passes_benchmark_and_walk_forward(uptrend_data_feed):
    config = ValidationConfig(
        active_campaigns=[ValidationCampaignType.WALK_FORWARD, ValidationCampaignType.BENCHMARK],
        markets=[Symbol("CRASH1000", AssetClass.INDICES)],
        timeframes=[TimeFrame.M1]
    )
    
    res_wf = WalkForwardValidator().run(WinningStrategy(), uptrend_data_feed, SimulatedBroker, config)
    res_bm = BenchmarkValidator().run(WinningStrategy(), uptrend_data_feed, SimulatedBroker, config)
    
    assert res_wf.details["folds_evaluated"] > 1
    assert res_bm.metrics["alpha"] >= 0.0
    assert "benchmark_sharpe" in res_bm.metrics
    assert res_bm.passed is True
