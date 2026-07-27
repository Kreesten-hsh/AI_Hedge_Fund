import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.research import ResearchMetadata
from aegis_trade.infrastructure.research.research_engine import ResearchEngine

@pytest.fixture
def dummy_metadata():
    return ResearchMetadata(
        symbol=Symbol("BTCUSD", AssetClass.CRYPTO),
        timeframe=TimeFrame.D1,
        start_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2023, 2, 9, tzinfo=timezone.utc),
        forward_returns_lag=1
    )

@pytest.fixture
def dummy_features():
    features = []
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    
    # We create 40 periods.
    # Feature 1: perfect predictor (same as future return)
    # Feature 2: random noise
    # Feature 3: constant (should handle 0 variance)
    # Feature 4: has NaNs
    
    np.random.seed(42)
    returns = np.random.normal(0, 0.01, 40)
    
    for i in range(40):
        # future return at t is returns[t+1]
        feature1 = returns[i+1] if i < 39 else 0.0
        
        fs = FeatureSet(
            symbol=Symbol("BTCUSD", AssetClass.CRYPTO),
            timeframe=TimeFrame.D1,
            timestamp=base_time + timedelta(days=i),
            features={
                "return_1d": float(returns[i]),
                "feat_perfect": float(feature1),
                "feat_noise": float(np.random.normal(0, 1)),
                "feat_constant": 5.0,
                "feat_nans": float(feature1) if i > 10 else None
            }
        )
        features.append(fs)
    return features

def test_research_engine_evaluate(dummy_features, dummy_metadata):
    engine = ResearchEngine()
    result = engine.evaluate(dummy_features, dummy_metadata)
    
    assert result.metadata.forward_returns_lag == 1
    assert "feat_perfect" in result.feature_scores
    
    score_perfect = result.feature_scores["feat_perfect"]
    score_constant = result.feature_scores["feat_constant"]
    score_noise = result.feature_scores["feat_noise"]
    score_nans = result.feature_scores["feat_nans"]
    
    # Constant feature should have 0 variance, 0 IC, 0 IR
    assert score_constant.variance == 0.0
    assert score_constant.ic_mean == 0.0
    assert score_constant.ic_information_ratio == 0.0
    
    # Perfect feature should have high IC
    assert score_perfect.ic_mean > 0.8  # It should be extremely close to 1
    assert score_perfect.ic_information_ratio > 1.0 # High IR
    
    # Noise should have low IC
    assert abs(score_noise.ic_mean) < 0.3
    
    # Missing rate check
    assert score_nans.missing_rate > 0.25 # 11 Nans out of 40 = 27.5%
    
    # Check Rankings
    assert "feat_perfect" in result.top_features
    # Noise or Constant should have significantly lower scores than Perfect
    assert score_perfect.final_score > score_noise.final_score
    assert score_perfect.final_score > score_constant.final_score

def test_research_engine_empty_features(dummy_metadata):
    engine = ResearchEngine()
    with pytest.raises(ValueError, match="No features provided"):
        engine.evaluate([], dummy_metadata)

def test_research_engine_no_returns(dummy_features, dummy_metadata):
    # Remove return_1d
    for fs in dummy_features:
        fs.features.pop("return_1d")
        
    engine = ResearchEngine()
    with pytest.raises(ValueError, match="return_1d must be present"):
        engine.evaluate(dummy_features, dummy_metadata)
