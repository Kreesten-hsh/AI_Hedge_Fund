import pytest
from datetime import datetime, timezone

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.infrastructure.strategies.composite import CompositeStrategy

SYMBOL = Symbol("TEST", AssetClass.CRYPTO)
TF = TimeFrame.D1
TS = datetime(2023, 1, 1, tzinfo=timezone.utc)


def _fs(features: dict | None = None) -> FeatureSet:
    return FeatureSet(
        symbol=SYMBOL,
        timeframe=TF,
        timestamp=TS,
        features=features or {},
    )


class AlwaysLongStrategy(IStrategy):
    def generate_signals(self, features: FeatureSet):
        return [Signal(symbol=features.symbol, direction=1, strength=0.8, timestamp=features.timestamp)]


class AlwaysShortStrategy(IStrategy):
    def generate_signals(self, features: FeatureSet):
        return [Signal(symbol=features.symbol, direction=-1, strength=0.8, timestamp=features.timestamp)]


class SilentStrategy(IStrategy):
    """Returns no signals."""
    def generate_signals(self, features: FeatureSet):
        return []


class TestCompositeStrategy:
    def test_two_longs_amplify(self):
        """Two strategies agreeing on LONG should produce a LONG signal."""
        composite = CompositeStrategy(
            strategies=[(AlwaysLongStrategy(), 1.0), (AlwaysLongStrategy(), 1.0)],
            threshold=0.3,
        )
        signals = composite.generate_signals(_fs())
        assert len(signals) == 1
        assert signals[0].direction == 1

    def test_two_shorts_amplify(self):
        """Two strategies agreeing on SHORT should produce a SHORT signal."""
        composite = CompositeStrategy(
            strategies=[(AlwaysShortStrategy(), 1.0), (AlwaysShortStrategy(), 1.0)],
            threshold=0.3,
        )
        signals = composite.generate_signals(_fs())
        assert len(signals) == 1
        assert signals[0].direction == -1

    def test_opposing_signals_cancel_out(self):
        """One LONG and one SHORT with equal weight should cancel and produce no signal."""
        composite = CompositeStrategy(
            strategies=[(AlwaysLongStrategy(), 1.0), (AlwaysShortStrategy(), 1.0)],
            threshold=0.3,
        )
        signals = composite.generate_signals(_fs())
        assert signals == []

    def test_asymmetric_weights_break_tie(self):
        """Heavier weight on LONG should break the tie in favour of LONG."""
        composite = CompositeStrategy(
            strategies=[(AlwaysLongStrategy(), 3.0), (AlwaysShortStrategy(), 1.0)],
            threshold=0.3,
        )
        # Score: (1*3 + (-1)*1) / (3+1) = 2/4 = 0.5 > 0.3 -> LONG
        signals = composite.generate_signals(_fs())
        assert len(signals) == 1
        assert signals[0].direction == 1

    def test_threshold_filters_weak_signal(self):
        """With a high threshold, even a mild majority should produce no signal."""
        composite = CompositeStrategy(
            strategies=[(AlwaysLongStrategy(), 1.0), (AlwaysShortStrategy(), 0.8)],
            threshold=0.5,
        )
        # Score: (1*1 + (-1)*0.8) / (1+0.8) = 0.2 / 1.8 = 0.111 < 0.5 -> no signal
        signals = composite.generate_signals(_fs())
        assert signals == []

    def test_all_silent_returns_empty(self):
        """If no sub-strategy emits signals, composite returns empty."""
        composite = CompositeStrategy(
            strategies=[(SilentStrategy(), 1.0), (SilentStrategy(), 1.0)],
            threshold=0.3,
        )
        assert composite.generate_signals(_fs()) == []

    def test_one_silent_one_active(self):
        """If one strategy is silent, only the active one counts."""
        composite = CompositeStrategy(
            strategies=[(AlwaysLongStrategy(), 1.0), (SilentStrategy(), 1.0)],
            threshold=0.3,
        )
        # Score: (1*1) / (1+1) = 0.5 > 0.3 -> LONG
        signals = composite.generate_signals(_fs())
        assert len(signals) == 1
        assert signals[0].direction == 1

    def test_strength_is_bounded(self):
        composite = CompositeStrategy(
            strategies=[(AlwaysLongStrategy(), 1.0), (AlwaysLongStrategy(), 1.0)],
            threshold=0.1,
        )
        signals = composite.generate_signals(_fs())
        assert 0.0 <= signals[0].strength <= 1.0

    def test_empty_strategies_raises(self):
        with pytest.raises(ValueError, match="at least one"):
            CompositeStrategy(strategies=[], threshold=0.3)

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="strictly positive"):
            CompositeStrategy(
                strategies=[(AlwaysLongStrategy(), 1.0)],
                threshold=0.0,
            )
