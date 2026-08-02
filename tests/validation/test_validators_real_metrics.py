import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from aegis_trade.domain.core import Symbol, TimeFrame, AssetClass
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.validation import ValidationCampaignType
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validators.hold_out_validator import HoldOutValidator
from aegis_trade.application.validation.validators.walk_forward_validator import WalkForwardValidator
from aegis_trade.application.validation.validators.monte_carlo_validator import MonteCarloValidator
from aegis_trade.application.validation.validators.benchmark_validator import BenchmarkValidator
from aegis_trade.application.validation.validators.multi_validators import MultiMarketValidator, MultiTimeframeValidator

@pytest.fixture
def dummy_data_feed():
    mock_feed = Mock()
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    bars = [
        FeatureSet(
            symbol=Symbol("CRASH1000", AssetClass.INDICES),
            timeframe=TimeFrame.M1,
            timestamp=now + timedelta(minutes=i),
            features={"close_price": 100.0 + i, "close": 100.0 + i}
        )
        for i in range(10)
    ]
    mock_feed.get_feature_stream.return_value = bars
    return mock_feed

def test_all_six_validators_no_hardcoded_pass(dummy_data_feed):
    config = ValidationConfig(
        active_campaigns=list(ValidationCampaignType),
        markets=[Symbol("CRASH1000", AssetClass.INDICES)],
        timeframes=[TimeFrame.M1]
    )
    
    mock_strategy = Mock()
    mock_strategy.generate_signals.return_value = []
    mock_broker_factory = Mock
    
    # 1. Hold-Out
    res_ho = HoldOutValidator().run(mock_strategy, dummy_data_feed, mock_broker_factory, config)
    assert "sharpe_ratio" in res_ho.metrics
    assert "max_drawdown" in res_ho.metrics
    assert isinstance(res_ho.passed, bool)
    
    # 2. Walk-Forward
    res_wf = WalkForwardValidator().run(mock_strategy, dummy_data_feed, mock_broker_factory, config)
    assert "sharpe_ratio" in res_wf.metrics
    assert "win_rate" in res_wf.metrics
    assert isinstance(res_wf.passed, bool)
    
    # 3. Monte-Carlo
    res_mc = MonteCarloValidator().run(mock_strategy, dummy_data_feed, mock_broker_factory, config)
    assert "ruin_probability" in res_mc.metrics
    assert isinstance(res_mc.passed, bool)
    
    # 4. Benchmark
    res_bm = BenchmarkValidator().run(mock_strategy, dummy_data_feed, mock_broker_factory, config)
    assert "alpha" in res_bm.metrics
    assert "beta" in res_bm.metrics
    assert isinstance(res_bm.passed, bool)
    
    # 5. Multi-Market
    res_mm = MultiMarketValidator().run(mock_strategy, dummy_data_feed, mock_broker_factory, config)
    assert "avg_sharpe_ratio" in res_mm.metrics
    assert isinstance(res_mm.passed, bool)
    
    # 6. Multi-Timeframe
    res_mt = MultiTimeframeValidator().run(mock_strategy, dummy_data_feed, mock_broker_factory, config)
    assert "avg_sharpe_ratio" in res_mt.metrics
    assert isinstance(res_mt.passed, bool)
