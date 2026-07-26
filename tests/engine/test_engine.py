import unittest
from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.domain import Symbol, AssetClass, MarketBar
from aegis_trade.dataset.domain import Dataset
from aegis_trade.dataset.resolver import DatasetResolver
from aegis_trade.engine.broker import SimulatedBroker
from aegis_trade.engine.core import TradingEngine
from aegis_trade.engine.feed import HistoricalReplayFeed
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.engine.risk import BasicRiskEngine
from aegis_trade.engine.strategy import EmaCrossStrategy


class MockDatasetResolver(DatasetResolver):
    def __init__(self, bars: list[MarketBar]):
        self.bars = bars

    def load_data(self, dataset: Dataset) -> list[MarketBar]:
        return self.bars


class TestTradingEngine(unittest.TestCase):
    def test_ema_cross_engine_e2e(self):
        symbol = Symbol("EURUSD", AssetClass.FOREX)
        
        # Create a synthetic dataset that will force an SMA cross
        bars = []
        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        
        # 1. 20 bars of flat price at 1.0 (SMA20 = 1.0, SMA50 = 1.0)
        # Actually SmaCrossStrategy needs 50 bars to warm up
        for i in range(51):
            bars.append(MarketBar(
                symbol=symbol,
                timeframe="M5",
                timestamp=base_time,
                open=Decimal("1.0"),
                high=Decimal("1.0"),
                low=Decimal("1.0"),
                close=Decimal("1.0"),
                volume=Decimal("100")
            ))
            
        # 2. Price drops to 0.5 for a few bars -> fast EMA < slow EMA -> ENTER_SHORT
        for i in range(5):
            bars.append(MarketBar(
                symbol=symbol,
                timeframe="M5",
                timestamp=base_time,
                open=Decimal("0.5"),
                high=Decimal("0.5"),
                low=Decimal("0.5"),
                close=Decimal("0.5"),
                volume=Decimal("100")
            ))
            
        # 3. Price spikes to 2.0 -> fast EMA > slow EMA -> ENTER_LONG
        for i in range(20):
            bars.append(MarketBar(
                symbol=symbol,
                timeframe="M5",
                timestamp=base_time,
                open=Decimal("2.0"),
                high=Decimal("2.0"),
                low=Decimal("2.0"),
                close=Decimal("2.0"),
                volume=Decimal("100")
            ))

        mock_resolver = MockDatasetResolver(bars)
        from aegis_trade.domain import TimeFrame
        mock_dataset = Dataset("hash", symbol, TimeFrame("M5"), len(bars), base_time, base_time)
        
        feed = HistoricalReplayFeed(mock_dataset, mock_resolver)
        strategy = EmaCrossStrategy(fast_period=20, slow_period=50)
        broker = SimulatedBroker(commission_per_unit=Decimal("0.0"), slippage_per_unit=Decimal("0.0"))
        risk = BasicRiskEngine(risk_pct=Decimal("0.10"))
        portfolio = Portfolio(initial_capital=10000.0)
        
        engine = TradingEngine(
            feed=feed,
            strategy=strategy,
            broker=broker,
            risk_engine=risk,
            portfolio=portfolio
        )
        
        report = engine.run()
        
        # Validate metrics
        self.assertIn("net_profit", report.metrics)
        self.assertTrue(report.metrics["total_trades"] > 0)
        
        # Verify equity curve length is at least total bars
        self.assertGreaterEqual(len(report.equity_curve), len(bars))
        
        # The engine must have closed all positions at the end
        self.assertEqual(len(portfolio._positions), 0)
