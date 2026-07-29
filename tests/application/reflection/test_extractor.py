from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.domain.core import Symbol, AssetClass, MarketBar, TimeFrame
from aegis_trade.domain.memory import MarketSession
from aegis_trade.application.reflection.extractor import LiveFeatureExtractor
from aegis_trade.application.reflection.snapshot import RichMarketSnapshot
import pandas as pd

def create_snapshot(bar: MarketBar) -> RichMarketSnapshot:
    df = pd.DataFrame([{
        'timestamp': bar.timestamp, 'open': float(bar.open), 'high': float(bar.high),
        'low': float(bar.low), 'close': float(bar.close), 'volume': float(bar.volume)
    }])
    return RichMarketSnapshot(symbol=bar.symbol, timestamp=bar.timestamp, latest_bar=bar, history=df)


def test_live_feature_extractor() -> None:
    extractor = LiveFeatureExtractor()
    
    symbol = Symbol("AAPL", AssetClass.EQUITIES)
    # Using 14:30 UTC for session logic
    timestamp = datetime(2023, 1, 1, 14, 30, tzinfo=timezone.utc)
    
    bar = MarketBar(
        symbol=symbol,
        timeframe=TimeFrame.M1,
        timestamp=timestamp,
        open=Decimal("150.0"),
        high=Decimal("155.0"),
        low=Decimal("149.0"),
        close=Decimal("152.0"),
        volume=Decimal("1000000")
    )
    
    features = extractor.extract(create_snapshot(bar))
    
    assert features.price == 152.0
    assert features.open_price == 150.0
    assert features.high_price == 155.0
    assert features.low_price == 149.0
    assert features.close_price == 152.0
    assert features.volume == 1000000.0
    assert features.spread == 0.0001
    
    # 14 * 60 + 30 = 870
    assert features.time_of_day == 870
    assert features.session == MarketSession.LONDON
    
    assert features.atr == (155.0 - 149.0)
    
def test_live_feature_extractor_sessions() -> None:
    extractor = LiveFeatureExtractor()
    symbol = Symbol("AAPL", AssetClass.EQUITIES)
    
    bar_tokyo = MarketBar(
        symbol=symbol, timeframe=TimeFrame.M1,
        timestamp=datetime(2023, 1, 1, 4, 30, tzinfo=timezone.utc),
        open=Decimal("150"), high=Decimal("151"), low=Decimal("149"), close=Decimal("150"), volume=Decimal("100")
    )
    assert extractor.extract(create_snapshot(bar_tokyo)).session == MarketSession.TOKYO
    
    bar_ny = MarketBar(
        symbol=symbol, timeframe=TimeFrame.M1,
        timestamp=datetime(2023, 1, 1, 16, 30, tzinfo=timezone.utc),
        open=Decimal("150"), high=Decimal("151"), low=Decimal("149"), close=Decimal("150"), volume=Decimal("100")
    )
    assert extractor.extract(create_snapshot(bar_ny)).session == MarketSession.NEW_YORK
    
    bar_asian = MarketBar(
        symbol=symbol, timeframe=TimeFrame.M1,
        timestamp=datetime(2023, 1, 1, 23, 30, tzinfo=timezone.utc),
        open=Decimal("150"), high=Decimal("151"), low=Decimal("149"), close=Decimal("150"), volume=Decimal("100")
    )
    assert extractor.extract(create_snapshot(bar_asian)).session == MarketSession.ASIAN_BOX
