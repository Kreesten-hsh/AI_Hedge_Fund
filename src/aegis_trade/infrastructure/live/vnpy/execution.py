from typing import Any, Awaitable, Callable, Optional
from datetime import datetime, timezone

from aegis_trade.domain.ports.broker import IExecutionGateway
from aegis_trade.engine.events import OrderEvent, OrderLifecycleEvent
from aegis_trade.engine.risk_gate import RiskGate

class VnPyExecutionGateway(IExecutionGateway):
    def __init__(
        self,
        main_engine,
        event_publisher: Callable[[Any], Awaitable[None]],
        symbol_mapper,
        risk_gate: Optional[RiskGate] = None,
    ):
        self.main_engine = main_engine
        self.event_publisher = event_publisher
        self.symbol_mapper = symbol_mapper
        # Voir VnpyAdapter : pas de porte de risque, pas de routage.
        self.risk_gate = risk_gate

    async def send_order(self, order: OrderEvent, latest_prices: Optional[dict] = None):
        """
        Translates an Aegis OrderEvent into a vn.py OrderRequest and sends it.

        Lève `OrderRejectedByRisk` si le RiskEngine refuse, `RuntimeError` si
        aucune porte de risque n'a été injectée.
        """
        if self.risk_gate is None:
            raise RuntimeError(
                "VnPyExecutionGateway sans RiskGate : aucun ordre ne peut être "
                "routé. Injecter un RiskGate à la construction."
            )
        self.risk_gate.authorize(order, latest_prices)

        from vnpy.trader.object import OrderRequest, Direction, OrderType
        
        # Translate OrderAction
        direction = Direction.LONG if order.action.value == "buy" else Direction.SHORT
        
        # Translate Symbol
        vt_symbol = self.symbol_mapper.to_vnpy_symbol(order.symbol)
        symbol, exchange = vt_symbol.split(".")
        from vnpy.trader.constant import Exchange
        try:
            exchange_enum = Exchange(exchange)
        except ValueError:
            # Fallback to a default if not strictly matched in vnpy constants
            exchange_enum = Exchange.LOCAL

        # Build OrderRequest
        req = OrderRequest(
            symbol=symbol,
            exchange=exchange_enum,
            direction=direction,
            type=OrderType.MARKET if order.order_type == "market" else OrderType.LIMIT,
            volume=float(order.volume),
            price=0.0, # Market order
            reference="AegisOS"
        )
        
        # Send via MainEngine
        # Assume self.gateway_name is configured or we use default
        gateway_name = exchange # simplification
        vt_orderid = self.main_engine.send_order(req, gateway_name)
        
        # Publish Submitted Event immediately
        event = OrderLifecycleEvent(
            order_id=vt_orderid,
            status="submitted",
            timestamp=datetime.now(timezone.utc)
        )
        await self.event_publisher(event)

    async def on_order(self, order):
        """
        Callback from vn.py for EVENT_ORDER.
        Translates back to Aegis OrderLifecycleEvent.
        """
        event = OrderLifecycleEvent(
            order_id=order.vt_orderid,
            status=order.status.value,
            timestamp=datetime.now(timezone.utc)
        )
        await self.event_publisher(event)
        
    async def on_trade(self, trade):
        """
        Callback from vn.py for EVENT_TRADE.
        Translates back to Aegis FillEvent or PositionEvent.
        """
        # This requires translation of vn.py TradeData to Aegis FillEvent
        # Left as a stub for the architecture outline
        pass
