from aegis_trade.domain.ports.position_sizer import IPositionSizer
from aegis_trade.domain.signal import Signal

class FixedFractionalSizer(IPositionSizer):
    def __init__(self, fraction: float = 0.95):
        self.fraction = fraction
        
    def size(self, signal: Signal, capital: float, current_price: float) -> float:
        if current_price <= 0:
            return 0.0
        return (capital * self.fraction) / current_price
