from abc import ABC, abstractmethod
from decimal import Decimal

from aegis_trade.engine.events import SignalEvent, OrderEvent, OrderAction, SignalIntent
from aegis_trade.engine.portfolio import Portfolio


class RiskEngine(ABC):
    """
    Interface for the Risk Engine.
    Converts SignalEvents into OrderEvents after applying position sizing and risk checks.
    """
    @abstractmethod
    def on_signal_event(self, event: SignalEvent, portfolio: Portfolio) -> list[OrderEvent]:
        pass


class BasicRiskEngine(RiskEngine):
    """
    Minimal Risk Engine for pipeline validation.
    Sizes trades as a percentage of current equity.
    """
    def __init__(self, risk_pct: Decimal = Decimal("0.10")):
        self._risk_pct = risk_pct

    def on_signal_event(self, event: SignalEvent, portfolio: Portfolio) -> list[OrderEvent]:
        orders = []
        current_pos = portfolio.get_position(event.symbol)
        latest_price = portfolio.get_latest_price(event.symbol)
        
        if latest_price is None or latest_price <= 0:
            return [] # Cannot size without price

        # Calculate target volume based on equity %
        # Example: 10% of $10,000 = $1,000 to allocate. At price 1.05, volume = 1000 / 1.05 ~ 952.
        target_volume = (portfolio.equity * self._risk_pct) / latest_price
        
        # Round to 2 decimal places to allow micro units (important for high-priced assets like XAUUSD)
        target_volume = round(target_volume, 2)
        
        if target_volume <= 0:
            return []

        if event.intent == SignalIntent.ENTER_LONG:
            if current_pos is None:
                orders.append(OrderEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    action=OrderAction.BUY,
                    volume=target_volume,
                    strategy_id=event.strategy_id
                ))
            elif current_pos.volume < 0: # Currently Short
                # Close Short
                orders.append(OrderEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    action=OrderAction.BUY,
                    volume=abs(current_pos.volume),
                    strategy_id=event.strategy_id
                ))
                # Open Long
                orders.append(OrderEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    action=OrderAction.BUY,
                    volume=target_volume,
                    strategy_id=event.strategy_id
                ))
        
        elif event.intent == SignalIntent.ENTER_SHORT:
            if current_pos is None:
                orders.append(OrderEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    action=OrderAction.SELL,
                    volume=target_volume,
                    strategy_id=event.strategy_id
                ))
            elif current_pos.volume > 0: # Currently Long
                # Close Long
                orders.append(OrderEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    action=OrderAction.SELL,
                    volume=current_pos.volume,
                    strategy_id=event.strategy_id
                ))
                # Open Short
                orders.append(OrderEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    action=OrderAction.SELL,
                    volume=target_volume,
                    strategy_id=event.strategy_id
                ))
                
        elif event.intent == SignalIntent.EXIT_LONG and current_pos is not None and current_pos.volume > 0:
            orders.append(OrderEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                action=OrderAction.SELL,
                volume=current_pos.volume,
                strategy_id=event.strategy_id
            ))
            
        elif event.intent == SignalIntent.EXIT_SHORT and current_pos is not None and current_pos.volume < 0:
            orders.append(OrderEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                action=OrderAction.BUY,
                volume=abs(current_pos.volume),
                strategy_id=event.strategy_id
            ))

        return orders
