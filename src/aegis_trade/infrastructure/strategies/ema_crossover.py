from typing import List

from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.strategy import IStrategy


class EmaCrossoverStrategy(IStrategy):
    """
    Trend-following strategy based on EMA crossover.
    Generates LONG when the fast EMA crosses above the slow EMA,
    SHORT when it crosses below. Returns no signal if features are missing.
    """

    def __init__(self, fast_key: str = "ema_10", slow_key: str = "ema_50"):
        self.fast_key = fast_key
        self.slow_key = slow_key
        self._prev_fast: float | None = None
        self._prev_slow: float | None = None

    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        fast = features.features.get(self.fast_key)
        slow = features.features.get(self.slow_key)

        if fast is None or slow is None:
            return []

        signals: List[Signal] = []

        if self._prev_fast is not None and self._prev_slow is not None:
            prev_spread = self._prev_fast - self._prev_slow
            curr_spread = fast - slow

            # Crossover detection: sign change in spread
            if prev_spread <= 0 < curr_spread:
                # Fast just crossed above slow -> bullish
                signals.append(Signal(
                    symbol=features.symbol,
                    direction=1,
                    strength=min(abs(curr_spread / slow) if slow != 0 else 1.0, 1.0),
                    timestamp=features.timestamp,
                ))
            elif prev_spread >= 0 > curr_spread:
                # Fast just crossed below slow -> bearish
                signals.append(Signal(
                    symbol=features.symbol,
                    direction=-1,
                    strength=min(abs(curr_spread / slow) if slow != 0 else 1.0, 1.0),
                    timestamp=features.timestamp,
                ))

        self._prev_fast = fast
        self._prev_slow = slow

        return signals
