import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, call

from aegis_trade.domain import Symbol, AssetClass
from aegis_trade.engine.events import OrderEvent, OrderAction, FillEvent
from aegis_trade.providers.vnpy_adapter import VnpyAdapter, EVENT_TRADE, Direction, OrderType, Exchange, Offset

class TestVnpyAdapter(unittest.TestCase):
    def setUp(self):
        self.mock_main_engine = Mock()
        self.mock_event_engine = Mock()
        self.adapter = VnpyAdapter(main_engine=self.mock_main_engine, event_engine=self.mock_event_engine, gateway_name="TEST")
        
    def test_adapter_registers_event(self):
        self.mock_event_engine.register.assert_called_once_with(EVENT_TRADE, self.adapter.on_trade)

    def test_send_order_translates_correctly(self):
        ts = datetime.now(timezone.utc)
        sym = Symbol("XAUUSD", AssetClass.COMMODITIES)
        
        # Aegis DTO
        aegis_order = OrderEvent(
            timestamp=ts,
            symbol=sym,
            action=OrderAction.BUY,
            volume=Decimal("1.5"),
            strategy_id="test_strat"
        )
        
        self.adapter.send_order(aegis_order)
        
        # Verify MainEngine called
        self.mock_main_engine.send_order.assert_called_once()
        args, kwargs = self.mock_main_engine.send_order.call_args
        
        vnpy_req = args[0]
        gateway = args[1]
        
        self.assertEqual(gateway, "TEST")
        self.assertEqual(vnpy_req.symbol, "XAUUSD")
        self.assertEqual(vnpy_req.direction, Direction.LONG)
        self.assertEqual(vnpy_req.type, OrderType.MARKET)
        self.assertEqual(vnpy_req.volume, 1.5)
        self.assertEqual(vnpy_req.reference, "test_strat")

    def test_on_trade_translates_correctly(self):
        ts = datetime.now(timezone.utc)
        
        # vn.py DTO mock
        mock_trade = Mock()
        mock_trade.symbol = "XAUUSD"
        mock_trade.direction = Direction.SHORT
        mock_trade.volume = 2.0
        mock_trade.price = 2000.5
        mock_trade.exchange = Exchange.SMART
        mock_trade.datetime = ts
        mock_trade.reference = "test_strat"
        
        mock_event = Mock()
        mock_event.data = mock_trade
        
        # Push to adapter
        self.adapter.on_trade(mock_event)
        
        # Verify queue
        fills = self.adapter.poll_fills()
        self.assertEqual(len(fills), 1)
        
        fill = fills[0]
        self.assertEqual(fill.symbol, "XAUUSD")
        self.assertEqual(fill.action, OrderAction.SELL)
        self.assertEqual(fill.volume, Decimal("2.0"))
        self.assertEqual(fill.fill_price, Decimal("2000.5"))
        self.assertEqual(fill.exchange, "SMART")
        self.assertEqual(fill.strategy_id, "test_strat")
        self.assertEqual(fill.timestamp, ts)

if __name__ == "__main__":
    unittest.main()
