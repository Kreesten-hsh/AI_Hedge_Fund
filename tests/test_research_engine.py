import pytest
import numpy as np
import math
from datetime import datetime, timezone, timedelta

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.research import ResearchMetadata
from aegis_trade.infrastructure.research.research_engine import (
    ResearchEngine,
    SIGNIFICANCE_T,
    _effective_observations,
    _rank_ic_t_stat,
)

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


# --- Significance block ---
#
# The only Alpha Research report on file reports ic_mean 0.9645 for macd_signal.
# A rank correlation of 0.96 with a forward return is not a discovery, it is a
# target leak — `scripts/generate_dummy_features.py` writes tomorrow's return
# plus noise into that column. These tests pin the two properties that let the
# engine say so: the IC must be a RANK correlation, and it must never be
# reported without the sample size that produced it.


def _series_features(columns: dict, length: int, symbol_name: str = "CRASH1000"):
    """Build a chronological FeatureSet list from column-wise arrays."""
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    return [
        FeatureSet(
            symbol=Symbol(symbol_name, AssetClass.CRYPTO),
            timeframe=TimeFrame.D1,
            timestamp=base_time + timedelta(days=i),
            features={name: float(values[i]) for name, values in columns.items()},
        )
        for i in range(length)
    ]


def _metadata(horizon: int, symbol_name: str = "CRASH1000"):
    return ResearchMetadata(
        symbol=Symbol(symbol_name, AssetClass.CRYPTO),
        timeframe=TimeFrame.D1,
        start_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        forward_returns_lag=horizon,
    )


class TestOverlapCorrection:
    def test_effective_sample_divides_by_horizon(self):
        """Forward windows overlap: only n/N observations are independent."""
        assert _effective_observations(1000, 10) == 100
        assert _effective_observations(1000, 1) == 1000

    def test_effective_sample_rejects_null_horizon(self):
        with pytest.raises(ValueError, match="horizon"):
            _effective_observations(1000, 0)

    def test_t_stat_shrinks_when_horizon_grows(self):
        """Same IC, longer horizon, fewer independent observations, smaller t.

        This is the whole point of the correction: reading a t off the raw count
        at N=10 inflates it by ~sqrt(10).
        """
        t_h1 = _rank_ic_t_stat(0.05, _effective_observations(10_000, 1))
        t_h10 = _rank_ic_t_stat(0.05, _effective_observations(10_000, 10))

        assert t_h1 > t_h10 > 0.0
        assert t_h1 / t_h10 == pytest.approx(10**0.5, rel=0.02)

    def test_t_stat_is_null_on_a_tiny_sample(self):
        assert _rank_ic_t_stat(0.9, 2) == 0.0

    def test_perfect_ic_stays_finite_and_large(self):
        """A leaking feature must rank loudly, not be silently zeroed.

        Zeroing an infinite t would bury exactly the signature the audit exists
        to catch.
        """
        t_stat = _rank_ic_t_stat(1.0, 500)

        assert math.isfinite(t_stat)
        assert t_stat > SIGNIFICANCE_T


class TestRankCorrelation:
    def test_ic_is_invariant_under_a_monotone_transform(self):
        """The decisive test that the IC is Spearman and not Pearson.

        A strictly increasing transform preserves every rank, so a rank
        correlation is unchanged by it. Pearson is not: cubing a feature
        redistributes its mass into the tails and moves the coefficient.
        """
        rng = np.random.default_rng(7)
        returns = rng.normal(0, 0.01, 400)
        raw = rng.normal(0, 1.0, 400)

        engine = ResearchEngine()
        plain = engine.evaluate(
            _series_features({"return_1d": returns, "feat": raw}, 400), _metadata(1)
        )
        # x**3 is strictly increasing on the reals: ranks are untouched.
        cubed = engine.evaluate(
            _series_features({"return_1d": returns, "feat": raw**3}, 400), _metadata(1)
        )

        assert plain.feature_scores["feat"].ic_spearman == pytest.approx(
            cubed.feature_scores["feat"].ic_spearman, abs=1e-9
        )
        assert plain.feature_scores["feat"].ic_mean == pytest.approx(
            cubed.feature_scores["feat"].ic_mean, abs=1e-9
        )

    def test_a_single_outlier_does_not_create_an_ic(self):
        """One bar must not carry the verdict.

        Feature and forward return are independent except that both spike on the
        same row. Pearson reads that one pair as a strong relation; a rank
        correlation gives it exactly one rank's worth of weight.
        """
        rng = np.random.default_rng(11)
        returns = rng.normal(0, 0.01, 300)
        feature = rng.normal(0, 1.0, 300)
        # Co-spike: huge feature value on the bar preceding a huge return.
        feature[100] = 500.0
        returns[101] = 5.0

        result = ResearchEngine().evaluate(
            _series_features({"return_1d": returns, "feat_spike": feature}, 300),
            _metadata(1),
        )

        assert abs(result.feature_scores["feat_spike"].ic_spearman) < 0.2


class TestSignificanceGate:
    def test_pure_noise_is_not_significant(self):
        """No relation, no significance, and no score — whatever the IR says."""
        rng = np.random.default_rng(3)
        returns = rng.normal(0, 0.01, 600)
        noise = rng.normal(0, 1.0, 600)

        result = ResearchEngine().evaluate(
            _series_features({"return_1d": returns, "feat_noise": noise}, 600),
            _metadata(5),
        )
        score = result.feature_scores["feat_noise"]

        assert abs(score.ic_spearman) < 0.15
        assert score.is_significant is False
        assert score.final_score == 0.0

    def test_a_leaking_feature_is_flagged(self):
        """Reproduces the 0.9645 signature: the target copied into a column.

        The engine must not be the thing that hides it — it must report an IC
        near 1 with a t that makes the anomaly obvious.
        """
        rng = np.random.default_rng(5)
        returns = rng.normal(0, 0.02, 400)
        # Tomorrow's return plus a little noise: `generate_dummy_features.py:...`
        leak = np.append(returns[1:], 0.0) + rng.normal(0, 0.005, 400)

        result = ResearchEngine().evaluate(
            _series_features({"return_1d": returns, "feat_leak": leak}, 400),
            _metadata(1),
        )
        score = result.feature_scores["feat_leak"]

        assert score.ic_spearman > 0.9
        assert score.is_significant is True
        assert score.ic_t_stat > 10.0

    def test_sample_sizes_are_reported_with_every_score(self):
        """An IC without its sample size cannot be argued with."""
        rng = np.random.default_rng(13)
        returns = rng.normal(0, 0.01, 500)
        feature = rng.normal(0, 1.0, 500)

        result = ResearchEngine().evaluate(
            _series_features({"return_1d": returns, "feat": feature}, 500),
            _metadata(10),
        )
        score = result.feature_scores["feat"]

        # Last 10 rows have no forward return: they are dropped by the mask.
        assert score.observations == 490
        assert score.effective_observations == 49

    def test_a_constant_feature_carries_no_significance(self):
        rng = np.random.default_rng(17)
        returns = rng.normal(0, 0.01, 200)

        result = ResearchEngine().evaluate(
            _series_features({"return_1d": returns, "feat_const": np.full(200, 5.0)}, 200),
            _metadata(5),
        )
        score = result.feature_scores["feat_const"]

        assert score.ic_spearman == 0.0
        assert score.is_significant is False
        assert score.final_score == 0.0
