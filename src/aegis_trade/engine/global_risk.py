from decimal import Decimal
from typing import Dict, Tuple, TYPE_CHECKING

from aegis_trade.domain import Symbol
from aegis_trade.engine.events import OrderEvent, OrderAction

if TYPE_CHECKING:
    from aegis_trade.engine.portfolio import Portfolio

class GlobalRiskManager:
    """
    Institutional Global Risk Governance.
    Acts as the final shield before an order is executed.
    """
    def __init__(
        self,
        max_gross_exposure: Decimal = Decimal("1.0"),
        max_drawdown: Decimal = Decimal("0.05"),
        max_concentration: Decimal = Decimal("0.20")
    ):
        self.max_gross_exposure = max_gross_exposure
        self.max_drawdown = max_drawdown
        self.max_concentration = max_concentration

    def validate_order(
        self,
        order: OrderEvent,
        portfolio: "Portfolio",
        latest_prices: dict[Symbol, Decimal]
    ) -> Tuple[bool, str]:
        """
        Validates if an order complies with the global risk limits.
        Returns a tuple (is_approved, rejection_reason).
        """
        if portfolio.equity <= 0:
            return False, "Portfolio equity is zero or negative."
            
        current_price = latest_prices.get(order.symbol)
        if current_price is None or current_price <= 0:
            return False, f"Missing or invalid price for {order.symbol.name}"

        # 1. Kill Switch (Max Drawdown)
        # Calculate High Water Mark
        hwm = portfolio.initial_capital
        for point in portfolio.equity_curve:
            if point.equity > hwm:
                hwm = point.equity
        
        current_drawdown = Decimal("0.0")
        if hwm > 0:
            current_drawdown = (hwm - portfolio.equity) / hwm
            
        is_opening_order = self._is_opening_order(order, portfolio)

        if current_drawdown >= self.max_drawdown and is_opening_order:
            return False, f"Kill Switch activated: Current drawdown {current_drawdown:.2%} exceeds limit {self.max_drawdown:.2%}"

        # 2. Max Concentration
        # Calculate new absolute position size for this symbol
        current_pos = portfolio.get_position(order.symbol)
        current_vol = current_pos.volume if current_pos else Decimal("0.0")
        
        # Simulate new volume
        order_qty = order.volume if order.action == OrderAction.BUY else -order.volume
        new_vol = current_vol + order_qty
        
        new_notional = abs(new_vol) * current_price
        concentration = new_notional / portfolio.equity
        
        if concentration > self.max_concentration:
            return False, f"Concentration limit exceeded: {concentration:.2%} > {self.max_concentration:.2%}"

        # 3. Max Gross Exposure
        # Calculate current total gross exposure across all symbols (excluding the order's symbol as we replaced it)
        total_gross = Decimal("0.0")
        for sym, pos in portfolio.open_positions.items():
            if sym != order.symbol:
                price = latest_prices.get(sym, Decimal("0.0"))
                total_gross += abs(pos.volume) * price
                
        # Add the new notional for the ordered symbol
        total_gross += new_notional
        
        gross_exposure = total_gross / portfolio.equity
        
        if gross_exposure > self.max_gross_exposure:
            return False, f"Gross Exposure limit exceeded: {gross_exposure:.2%} > {self.max_gross_exposure:.2%}"

        return True, ""

    def _is_opening_order(self, order: OrderEvent, portfolio: "Portfolio") -> bool:
        """Determines if an order increases the absolute position size."""
        current_pos = portfolio.get_position(order.symbol)
        if not current_pos:
            return True
            
        current_vol = current_pos.volume
        order_qty = order.volume if order.action == OrderAction.BUY else -order.volume
        
        # If current is long (>0) and order is buy (>0) -> Opening
        # If current is short (<0) and order is sell (<0) -> Opening
        if (current_vol > 0 and order_qty > 0) or (current_vol < 0 and order_qty < 0):
            return True
            
        return False
