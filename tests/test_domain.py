import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from aegis_trade.domain import (
    Symbol, AssetClass, TimeFrame, MarketBar, Tick, Position, Trade, Side, HealthStatus
)

class TestDomain(unittest.TestCase):
    def test_symbol_validation(self):
        with self.assertRaises(ValueError):
            Symbol(name="", asset_class=AssetClass.FOREX)
        
        sym = Symbol(name="EURUSD", asset_class=AssetClass.FOREX)
        self.assertEqual(sym.name, "EURUSD")
        self.assertEqual(sym.asset_class, AssetClass.FOREX)

    def test_timeframe_validation(self):
        tf = TimeFrame.H1
        self.assertEqual(tf.value, "H1")
        self.assertTrue(TimeFrame("M15") is TimeFrame.M15)

    def test_marketbar_validation(self):
        sym = Symbol("EURUSD", AssetClass.FOREX)
        tf = TimeFrame.H1
        utc_now = datetime.now(timezone.utc)
        naive_now = datetime.now()

        with self.assertRaises(ValueError):
            MarketBar(sym, tf, naive_now, Decimal("1.10"), Decimal("1.15"), Decimal("1.05"), Decimal("1.12"), Decimal("100"))
        
        with self.assertRaises(ValueError):
            MarketBar(sym, tf, utc_now, Decimal("-1.10"), Decimal("1.15"), Decimal("1.05"), Decimal("1.12"), Decimal("100"))
            
        with self.assertRaises(ValueError):
            MarketBar(sym, tf, utc_now, Decimal("1.10"), Decimal("1.00"), Decimal("1.05"), Decimal("1.12"), Decimal("100"))

        with self.assertRaises(ValueError):
            MarketBar(sym, tf, utc_now, Decimal("1.10"), Decimal("1.15"), Decimal("1.20"), Decimal("1.12"), Decimal("100"))
            
        with self.assertRaises(ValueError):
            MarketBar(sym, tf, utc_now, Decimal("1.10"), Decimal("1.15"), Decimal("1.05"), Decimal("1.12"), Decimal("-10"))

        bar = MarketBar(sym, tf, utc_now, Decimal("1.10"), Decimal("1.15"), Decimal("1.05"), Decimal("1.12"), Decimal("100"))
        self.assertEqual(bar.open, Decimal("1.10"))

    def test_tick_validation(self):
        sym = Symbol("EURUSD", AssetClass.FOREX)
        utc_now = datetime.now(timezone.utc)

        with self.assertRaises(ValueError):
            Tick(sym, datetime.now(), Decimal("1.10"), Decimal("1.11"))
        
        with self.assertRaises(ValueError):
            Tick(sym, utc_now, Decimal("1.12"), Decimal("1.11"))

        tick = Tick(sym, utc_now, Decimal("1.10"), Decimal("1.11"))
        self.assertEqual(tick.bid, Decimal("1.10"))

    def test_position_validation(self):
        sym = Symbol("EURUSD", AssetClass.FOREX)
        utc_now = datetime.now(timezone.utc)

        with self.assertRaises(ValueError):
            Position(sym, Side.LONG, Decimal("-1"), Decimal("1"), utc_now)
            
        with self.assertRaises(ValueError):
            Position(sym, Side.LONG, Decimal("1"), Decimal("0"), utc_now)

        pos = Position(sym, Side.LONG, Decimal("1.10"), Decimal("100"), utc_now)
        self.assertEqual(pos.volume, Decimal("100"))

    def test_trade_validation(self):
        sym = Symbol("EURUSD", AssetClass.FOREX)
        utc_now = datetime.now(timezone.utc)
        pos = Position(sym, Side.LONG, Decimal("1.10"), Decimal("100"), utc_now)

        with self.assertRaises(ValueError):
            Trade(pos, Decimal("0"), utc_now + timedelta(hours=1))

        with self.assertRaises(ValueError):
            Trade(pos, Decimal("1.12"), utc_now - timedelta(hours=1))
            
        trade = Trade(pos, Decimal("1.12"), utc_now + timedelta(hours=1))
        self.assertEqual(trade.exit_price, Decimal("1.12"))

    def test_health_status(self):
        hs = HealthStatus(connected=True, latency=0.1, provider="mt5", version="1.0", last_error=None)
        self.assertTrue(hs.connected)

if __name__ == '__main__':
    unittest.main()
