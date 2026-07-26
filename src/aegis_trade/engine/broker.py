from abc import ABC, abstractmethod
from decimal import Decimal

from aegis_trade.engine.events import OrderEvent, FillEvent, MarketEvent


class Broker(ABC):
    """
    Interface for the Event-Driven Broker.
    Consumes OrderEvents and produces FillEvents.
    """
    @abstractmethod
    def on_order_event(self, event: OrderEvent, latest_market_event: MarketEvent | None) -> FillEvent | None:
        pass


class SimulatedBroker(Broker):
    """
    Simulated Broker for backtesting and paper trading.
    Assumes instantaneous execution at the next available price (usually the close of the current bar in simple backtests, 
    or the open of the next bar. Here we use the latest market event's close price as a simplification).
    """
    def __init__(self, commission_per_unit: Decimal = Decimal("0.0"), slippage_per_unit: Decimal = Decimal("0.0")):
        self._commission_per_unit = commission_per_unit
        self._slippage_per_unit = slippage_per_unit

    def on_order_event(self, event: OrderEvent, latest_market_event: MarketEvent | None) -> FillEvent | None:
        if latest_market_event is None:
            return None # Cannot fill without market data
            
        # Execute at the open of the current bar to avoid look-ahead bias
        # (Assuming the order was placed before this bar opened)
        base_price = latest_market_event.bar.open
        
        # Add slippage
        # If BUY, price goes up. If SELL, price goes down.
        if event.action.value == "buy":
            fill_price = base_price + self._slippage_per_unit
        else:
            fill_price = base_price - self._slippage_per_unit
            
        commission = self._commission_per_unit * event.volume

        return FillEvent(
            timestamp=latest_market_event.timestamp,
            symbol=event.symbol,
            action=event.action,
            volume=event.volume,
            fill_price=fill_price,
            commission=commission,
            exchange="SIMULATED",
            strategy_id=event.strategy_id
        )
