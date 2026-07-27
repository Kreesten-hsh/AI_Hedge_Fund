import pytest
from datetime import datetime, timezone

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.infrastructure.strategies.ema_crossover import EmaCrossoverStrategy

SYMBOL = Symbol("TEST", AssetClass.CRYPTO)
TF = TimeFrame.D1


def _fs(ema_10: float | None, ema_50: float | None, day: int = 1) -> FeatureSet:
    features = {}
    if ema_10 is not None:
        features["ema_10"] = ema_10
    if ema_50 is not None:
        features["ema_50"] = ema_50
    return FeatureSet(
        symbol=SYMBOL,
        timeframe=TF,
        timestamp=datetime(2023, 1, day, tzinfo=timezone.utc),
        features=features,
    )


class TestEmaCrossoverStrategy:
    def test_bullish_crossover(self):
        strategy = EmaCrossoverStrategy()
        # Day 1: fast below slow (no signal, just primes state)
        assert strategy.generate_signals(_fs(48.0, 50.0, day=1)) == []
        # Day 2: fast crosses above slow -> LONG
        signals = strategy.generate_signals(_fs(52.0, 50.0, day=2))
        assert len(signals) == 1
        assert signals[0].direction == 1

    def test_bearish_crossover(self):
        strategy = EmaCrossoverStrategy()
        # Day 1: fast above slow
        assert strategy.generate_signals(_fs(52.0, 50.0, day=1)) == []
        # Day 2: fast crosses below slow -> SHORT
        signals = strategy.generate_signals(_fs(48.0, 50.0, day=2))
        assert len(signals) == 1
        assert signals[0].direction == -1

    def test_no_crossover_flat(self):
        strategy = EmaCrossoverStrategy()
        # Day 1: fast above slow
        strategy.generate_signals(_fs(52.0, 50.0, day=1))
        # Day 2: fast still above slow -> no crossover, no signal
        signals = strategy.generate_signals(_fs(53.0, 50.0, day=2))
        assert signals == []

    def test_missing_fast_ema_returns_empty(self):
        strategy = EmaCrossoverStrategy()
        signals = strategy.generate_signals(_fs(None, 50.0))
        assert signals == []

    def test_missing_slow_ema_returns_empty(self):
        strategy = EmaCrossoverStrategy()
        signals = strategy.generate_signals(_fs(52.0, None))
        assert signals == []

    def test_both_emas_missing_returns_empty(self):
        strategy = EmaCrossoverStrategy()
        fs = FeatureSet(
            symbol=SYMBOL,
            timeframe=TF,
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            features={},
        )
        assert strategy.generate_signals(fs) == []

    def test_strength_is_bounded(self):
        strategy = EmaCrossoverStrategy()
        strategy.generate_signals(_fs(10.0, 50.0, day=1))
        signals = strategy.generate_signals(_fs(90.0, 50.0, day=2))
        assert len(signals) == 1
        assert 0.0 <= signals[0].strength <= 1.0
