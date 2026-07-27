import pytest
from datetime import datetime, timezone

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.infrastructure.strategies.rsi_mean_reversion import RsiMeanReversionStrategy

SYMBOL = Symbol("TEST", AssetClass.CRYPTO)
TF = TimeFrame.D1


def _fs(rsi: float | None, day: int = 1) -> FeatureSet:
    features = {}
    if rsi is not None:
        features["rsi_14"] = rsi
    return FeatureSet(
        symbol=SYMBOL,
        timeframe=TF,
        timestamp=datetime(2023, 1, day, tzinfo=timezone.utc),
        features=features,
    )


class TestRsiMeanReversionStrategy:
    def test_oversold_generates_long(self):
        strategy = RsiMeanReversionStrategy()
        signals = strategy.generate_signals(_fs(25.0))
        assert len(signals) == 1
        assert signals[0].direction == 1

    def test_overbought_generates_short(self):
        strategy = RsiMeanReversionStrategy()
        signals = strategy.generate_signals(_fs(75.0))
        assert len(signals) == 1
        assert signals[0].direction == -1

    def test_neutral_rsi_returns_empty(self):
        strategy = RsiMeanReversionStrategy()
        signals = strategy.generate_signals(_fs(50.0))
        assert signals == []

    def test_exact_boundary_oversold_returns_empty(self):
        """RSI exactly at 30 is not < 30, so no signal."""
        strategy = RsiMeanReversionStrategy()
        signals = strategy.generate_signals(_fs(30.0))
        assert signals == []

    def test_exact_boundary_overbought_returns_empty(self):
        """RSI exactly at 70 is not > 70, so no signal."""
        strategy = RsiMeanReversionStrategy()
        signals = strategy.generate_signals(_fs(70.0))
        assert signals == []

    def test_missing_rsi_returns_empty(self):
        strategy = RsiMeanReversionStrategy()
        signals = strategy.generate_signals(_fs(None))
        assert signals == []

    def test_completely_empty_features_returns_empty(self):
        strategy = RsiMeanReversionStrategy()
        fs = FeatureSet(
            symbol=SYMBOL,
            timeframe=TF,
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            features={},
        )
        assert strategy.generate_signals(fs) == []

    def test_custom_thresholds(self):
        strategy = RsiMeanReversionStrategy(oversold=40.0, overbought=60.0)
        assert strategy.generate_signals(_fs(35.0))[0].direction == 1
        assert strategy.generate_signals(_fs(65.0))[0].direction == -1
        assert strategy.generate_signals(_fs(50.0)) == []

    def test_strength_proportional_to_depth(self):
        strategy = RsiMeanReversionStrategy()
        # RSI at 10 should have higher strength than RSI at 25
        sig_deep = strategy.generate_signals(_fs(10.0))
        sig_shallow = strategy.generate_signals(_fs(25.0))
        assert sig_deep[0].strength > sig_shallow[0].strength

    def test_strength_is_bounded(self):
        strategy = RsiMeanReversionStrategy()
        signals = strategy.generate_signals(_fs(0.0))
        assert 0.0 <= signals[0].strength <= 1.0
        signals = strategy.generate_signals(_fs(100.0))
        assert 0.0 <= signals[0].strength <= 1.0
