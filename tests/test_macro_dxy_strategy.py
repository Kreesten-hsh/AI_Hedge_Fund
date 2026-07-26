import pytest
from datetime import datetime, timezone
from decimal import Decimal
from aegis_trade.domain import (
    MarketBar, Symbol, AssetClass, TimeFrame
)
from aegis_trade.engine.events import MarketEvent, SignalEvent, SignalIntent
from aegis_trade.strategies.macro_dxy import MacroDxyStrategy

def test_macro_dxy_strategy_long_signal():
    ts = datetime(2024, 7, 25, 19, 0, tzinfo=timezone.utc)
    strategy = MacroDxyStrategy(symbol="XAUUSD", macro_data={ts: 0.02})
    
    # Event with DXY Mom5 > 0
    bar = MarketBar(
        symbol=Symbol("XAUUSD", AssetClass.FOREX),
        timeframe=TimeFrame.H1,
        timestamp=ts,
        open=Decimal("2000.0"), high=Decimal("2010.0"), low=Decimal("1990.0"), close=Decimal("2005.0"), volume=Decimal("100.0")
    )
    event = MarketEvent(timestamp=ts, bar=bar)
    
    signals = strategy.on_market_event(event)
    
    assert len(signals) == 1
    signal = signals[0]
    assert signal.intent == SignalIntent.ENTER_LONG
    assert signal.symbol.name == "XAUUSD"
    
def test_macro_dxy_strategy_short_signal():
    ts = datetime(2024, 7, 25, 20, 0, tzinfo=timezone.utc)
    strategy = MacroDxyStrategy(symbol="XAUUSD", macro_data={ts: -0.01})
    
    # Event with DXY Mom5 < 0
    bar = MarketBar(
        symbol=Symbol("XAUUSD", AssetClass.FOREX),
        timeframe=TimeFrame.H1,
        timestamp=ts,
        open=Decimal("2000.0"), high=Decimal("2010.0"), low=Decimal("1990.0"), close=Decimal("2005.0"), volume=Decimal("100.0")
    )
    event = MarketEvent(timestamp=ts, bar=bar)
    
    signals = strategy.on_market_event(event)
    
    assert len(signals) == 1
    signal = signals[0]
    assert signal.intent == SignalIntent.ENTER_SHORT
    assert signal.symbol.name == "XAUUSD"

def test_macro_dxy_strategy_no_signal_on_missing_feature():
    ts = datetime(2024, 7, 25, 21, 0, tzinfo=timezone.utc)
    strategy = MacroDxyStrategy(symbol="XAUUSD", macro_data={})
    
    bar = MarketBar(
        symbol=Symbol("XAUUSD", AssetClass.FOREX),
        timeframe=TimeFrame.H1,
        timestamp=ts,
        open=Decimal("2000.0"), high=Decimal("2010.0"), low=Decimal("1990.0"), close=Decimal("2005.0"), volume=Decimal("100.0")
    )
    event = MarketEvent(timestamp=ts, bar=bar)
    
    signals = strategy.on_market_event(event)
    
    assert len(signals) == 0
