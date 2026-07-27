from datetime import timezone
from decimal import Decimal
from typing import Tuple
from dataclasses import dataclass

from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.events import OrderEvent, OrderAction
from aegis_trade.domain.execution import OrderIntent
from aegis_trade.domain.core import Symbol


@dataclass
class _AdapterEquityPoint:
    equity: Decimal


@dataclass
class _AdapterPosition:
    volume: Decimal


class _AdapterPortfolio:
    """Minimal duck-typed portfolio for GlobalRiskManager."""
    def __init__(self, equity: float, initial_capital: float, equity_curve: dict, position_qty: float, position_symbol: Symbol):
        self.equity = Decimal(str(equity))
        self.initial_capital = Decimal(str(initial_capital))
        
        self.equity_curve = []
        for eq in equity_curve.values():
            self.equity_curve.append(_AdapterEquityPoint(Decimal(str(eq))))
            
        self.position_qty = Decimal(str(position_qty))
        self.position_symbol = position_symbol
        
        self.open_positions = {}
        if self.position_qty != 0:
            self.open_positions[self.position_symbol] = _AdapterPosition(self.position_qty)

    def get_position(self, symbol: Symbol) -> _AdapterPosition | None:
        if symbol == self.position_symbol and self.position_qty != 0:
            return _AdapterPosition(self.position_qty)
        return None


class GlobalRiskAdapter:
    def __init__(self, risk_manager: GlobalRiskManager):
        self.risk_manager = risk_manager
        
    def validate_intent(
        self, 
        intent: OrderIntent, 
        current_capital: float, 
        initial_capital: float, 
        equity_curve: dict, 
        current_position: float
    ) -> Tuple[bool, str]:
        
        action = OrderAction.BUY if intent.direction > 0 else OrderAction.SELL
        volume = Decimal(str(intent.quantity))
        
        ts = intent.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
            
        order_event = OrderEvent(
            timestamp=ts,
            symbol=intent.symbol,
            action=action,
            volume=volume,
            order_type="market",
            strategy_id="modular_adapter"
        )
        
        portfolio = _AdapterPortfolio(
            equity=current_capital, 
            initial_capital=initial_capital, 
            equity_curve=equity_curve, 
            position_qty=current_position,
            position_symbol=intent.symbol
        )
        
        latest_prices = {
            intent.symbol: Decimal(str(intent.target_price))
        }
        
        return self.risk_manager.validate_order(order_event, portfolio, latest_prices)  # type: ignore
