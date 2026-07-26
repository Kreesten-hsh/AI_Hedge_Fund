from decimal import Decimal
from typing import Optional, Callable
import logging

from aegis_trade.engine.events import OrderEvent, FillEvent, OrderAction, MarketEvent
from aegis_trade.engine.broker import Broker

# Try to import from vnpy, fallback to None for mock/paper trading demo if not installed
try:
    from vnpy.trader.engine import MainEngine, EventEngine
    from vnpy.trader.object import OrderRequest, TradeData
    from vnpy.trader.constant import Direction, OrderType, Exchange, Offset
    from vnpy.event import Event
    from vnpy.trader.event import EVENT_TRADE
except ImportError:
    MainEngine = type("MainEngine", (), {})
    EventEngine = type("EventEngine", (), {})
    class OrderRequest:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class TradeData:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class Direction:
        LONG = "LONG"
        SHORT = "SHORT"
    class OrderType:
        MARKET = "MARKET"
    class Exchange:
        SMART = "SMART"
    class Offset:
        OPEN = "OPEN"
        CLOSE = "CLOSE"
    Event = type("Event", (), {})
    EVENT_TRADE = "eTrade."

class VnpyAdapter(Broker):
    """
    Anti-Corruption Layer (ACL) for vn.py.
    Translates Aegis OrderEvents to vn.py OrderRequests, and listens for vn.py trades to emit FillEvents.
    """
    def __init__(self, main_engine: MainEngine, event_engine: EventEngine, gateway_name: str = "PAPER"):
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.gateway_name = gateway_name
        self.event_queue: list[FillEvent] = []
        
        # Register the callback
        if hasattr(self.event_engine, "register"):
            self.event_engine.register(EVENT_TRADE, self.on_trade)
            
    def on_order_event(self, event: OrderEvent, latest_market_event: Optional[MarketEvent]) -> Optional[FillEvent]:
        """
        Implementation of the Broker interface. 
        Asynchronous brokers return None here, and fills are pushed asynchronously.
        """
        self.send_order(event)
        return None

    def send_order(self, order_event: OrderEvent) -> str:
        """
        Converts Aegis OrderEvent to vn.py OrderRequest and sends it.
        """
        direction = Direction.LONG if order_event.action == OrderAction.BUY else Direction.SHORT
        
        # In a full system, you would resolve the Exchange and Offset. Using defaults for paper trading.
        req = OrderRequest(
            symbol=order_event.symbol.name,
            exchange=Exchange.SMART,
            direction=direction,
            type=OrderType.MARKET,
            volume=float(order_event.volume),
            price=0.0,
            offset=Offset.OPEN,
            reference=order_event.strategy_id
        )
        
        if hasattr(self.main_engine, "send_order"):
            vt_orderid = self.main_engine.send_order(req, self.gateway_name)
            logging.info(f"Routed order to vn.py: {vt_orderid}")
            return vt_orderid
        return "mock_id"

    def on_trade(self, event: Event) -> None:
        """
        Listens to vn.py trades, translates to Aegis FillEvent, and stores in the queue.
        """
        trade_data: TradeData = event.data
        
        action = OrderAction.BUY if trade_data.direction == Direction.LONG else OrderAction.SELL
        
        fill_event = FillEvent(
            timestamp=trade_data.datetime, # Assuming TradeData has datetime
            symbol=trade_data.symbol, # Needs to be resolved back to Symbol object in a real system
            action=action,
            volume=Decimal(str(trade_data.volume)),
            fill_price=Decimal(str(trade_data.price)),
            commission=Decimal("0.0"), # Normally fetched from trade_data or broker
            exchange=trade_data.exchange.value if hasattr(trade_data.exchange, "value") else str(trade_data.exchange),
            strategy_id=trade_data.reference if hasattr(trade_data, "reference") else "unknown"
        )
        
        self.event_queue.append(fill_event)
        logging.info(f"Received fill from vn.py: {trade_data.symbol} {trade_data.volume} @ {trade_data.price}")
        
    def poll_fills(self) -> list[FillEvent]:
        """
        Allows the TradingEngine to retrieve asynchronous fills.
        """
        fills = self.event_queue.copy()
        self.event_queue.clear()
        return fills
