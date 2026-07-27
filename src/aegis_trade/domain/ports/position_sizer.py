from abc import ABC, abstractmethod
from aegis_trade.domain.signal import Signal

class IPositionSizer(ABC):
    @abstractmethod
    def size(self, signal: Signal, capital: float, current_price: float) -> float:
        """Calculate the absolute position size (quantity) based on signal and capital."""
        pass
