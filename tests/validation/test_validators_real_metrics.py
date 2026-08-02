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
