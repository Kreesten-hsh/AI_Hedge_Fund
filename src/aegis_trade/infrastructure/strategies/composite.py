from typing import List, Tuple

from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.strategy import IStrategy


class CompositeStrategy(IStrategy):
    """
    Aggregates multiple sub-strategies via weighted voting.

    Each sub-strategy produces signals independently. The composite
    computes a weighted directional score and emits a single signal
    only when the score exceeds a configurable decision threshold.
    """

    def __init__(
        self,
        strategies: List[Tuple[IStrategy, float]],
        threshold: float = 0.3,
    ):
        """
        Args:
            strategies: List of (strategy, weight) pairs. Weights need not sum to 1;
                        they are normalised internally.
            threshold:  Minimum absolute weighted score to emit a directional signal.
                        Must be in (0, 1]. Default 0.3.
        """
        if not strategies:
            raise ValueError("CompositeStrategy requires at least one sub-strategy.")
        if threshold <= 0:
            raise ValueError("Threshold must be strictly positive.")

        self._strategies = strategies
        self._threshold = threshold

        total_weight = sum(abs(w) for _, w in strategies)
        if total_weight == 0:
            raise ValueError("Total weight must be non-zero.")
        self._total_weight = total_weight

    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        weighted_score = 0.0
        total_strength = 0.0
        contributing = 0

        for strategy, weight in self._strategies:
            signals = strategy.generate_signals(features)
            if not signals:
                continue

            # Aggregate all signals from a single sub-strategy
            for sig in signals:
                weighted_score += sig.direction * weight
                total_strength += sig.strength * abs(weight)
                contributing += 1

        if contributing == 0:
            return []

        # Normalise the score to [-1, 1]
        normalised_score = weighted_score / self._total_weight

        if abs(normalised_score) < self._threshold:
            return []

        direction = 1 if normalised_score > 0 else -1
        strength = min(total_strength / self._total_weight, 1.0)

        return [Signal(
            symbol=features.symbol,
            direction=direction,
            strength=strength,
            timestamp=features.timestamp,
        )]
