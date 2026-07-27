from typing import Optional

from aegis_trade.domain.execution import IBroker, OrderIntent, FillEvent

class SimulatedBroker(IBroker):
    """
    Simulates order execution by applying fixed commissions and simple slippage.
    """
    def __init__(self, commission_rate: float = 0.001, slippage_bps: float = 5.0):
        """
        Args:
            commission_rate: Flat fee per executed volume (e.g., 0.001 for 0.1%)
            slippage_bps: Slippage applied against the trader (in basis points, e.g. 5.0 for 0.05%)
        """
        self.commission_rate = commission_rate
        self.slippage_bps = slippage_bps

    def execute_order(self, order: OrderIntent) -> Optional[FillEvent]:
        if order.quantity <= 0:
            return None
            
        # Slippage works against the trade
        # Long trade: pay more. Short trade: receive less.
        slippage_factor = self.slippage_bps / 10000.0
        if order.direction > 0:
            fill_price = order.target_price * (1 + slippage_factor)
        else:
            fill_price = order.target_price * (1 - slippage_factor)
            
        # Commission is based on total value transacted
        trade_value = fill_price * order.quantity
        commission = trade_value * self.commission_rate
        
        return FillEvent(
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.quantity,
            fill_price=fill_price,
            commission=commission,
            timestamp=order.timestamp
        )
