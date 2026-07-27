from abc import ABC, abstractmethod
from typing import List

from aegis_trade.domain.signal import Signal
from aegis_trade.domain.features import FeatureSet

class IStrategy(ABC):
    """
    Port (Interface) for trading strategies.
    Strategies consume FeatureSets and emit Signals.
    """
    @abstractmethod
    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        """
        Evaluates current features and returns a list of generated signals (if any).
        """
        pass
