from aegis_trade.domain.ports.position_sizer import IPositionSizer
from aegis_trade.domain.signal import Signal

from typing import Optional

class FixedFractionalSizer(IPositionSizer):
    def __init__(self, fraction: float = 0.95, max_allowed_fraction: Optional[float] = None):
        self.fraction = fraction
        self.max_allowed_fraction = max_allowed_fraction
        
    def size(self, signal: Signal, capital: float, current_price: float) -> float:
        if current_price <= 0:
            return 0.0
        effective_fraction = min(self.fraction, self.max_allowed_fraction) if self.max_allowed_fraction is not None else self.fraction
        return (capital * effective_fraction) / current_price
