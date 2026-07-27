import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Iterator, List

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker
from aegis_trade.engine.backtester import Backtester

class MockDataFeed(IDataFeed):
    def get_feature_stream(self, symbol: Symbol, timeframe: TimeFrame) -> Iterator[FeatureSet]:
        base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        prices = [100.0, 102.0, 98.0, 105.0, 110.0]
        for i, p in enumerate(prices):
            yield FeatureSet(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=base_time + timedelta(days=i),
                features={'close_price': p}
            )

class MockStrategy(IStrategy):
    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        price = features.features['close_price']
        
        # Simple strategy: Buy when price <= 100, close when price >= 105
        direction = 0
        if price <= 100:
            direction = 1
        elif price >= 105:
            direction = -1
            
        return [Signal(
            symbol=features.symbol,
            direction=direction,
            strength=1.0,
            timestamp=features.timestamp
        )]

def test_backtester_run():
    symbol = Symbol("AAPL", AssetClass.EQUITIES)
    
    feed = MockDataFeed()
    strategy = MockStrategy()
    broker = SimulatedBroker(commission_rate=0.0, slippage_bps=0.0) # Zero friction for easy math
    
    backtester = Backtester(data_feed=feed, strategy=strategy, broker=broker, starting_capital=100000.0)
    
    report = backtester.run(symbol, TimeFrame.D1)
    
    # Trace the logic:
    # T0 (Price=100): Capital=100k, Sig=1. Buys: (100k*0.95)/100 = 950 units. Equity=100k
    # T1 (Price=102): Pos=950. Unrlzd=950*2=1900. Eq=101900. Sig=0.
    # T2 (Price=98): Pos=950. Unrlzd=950*-2=-1900. Eq=98100. Sig=1 (already long, no new pos)
    # T3 (Price=105): Pos=950. Unrlzd=950*5=4750. Eq=104750. Sig=-1. Sells 950 to close, then goes short?
    #   Wait, our backtester closes first if pos != 0 and sig == 0, but for sig == -1 when pos > 0, 
    #   the backtester logic says: target_qty = -qty. 
    #   qty = (104750 * 0.95) / 105 = 947.7. target_qty = -947.7.
    #   order_qty = abs(-947.7 - 950) = 1897.7 to sell.
    #   Fill at 105.
    #   Realized PnL from closing long: (105 - 100) * 950 = 4750. Capital becomes 104750.
    #   Position becomes -947.7. Average price = 105.
    # T4 (Price=110): Pos=-947.7. Unrlzd = (105 - 110) * -947.7 = -4738.5. 
    #   Eq = 104750 - 4738.5 = 100011.5. Sig=-1.
    
    assert report is not None
    assert "total_return" in report.to_dict()
    assert report.total_return > 0.0 # Started at 100k, ended at ~100011.5
