import pytest
from datetime import datetime, timezone
from decimal import Decimal
from aegis_trade.domain import (
    MarketBar, Symbol, AssetClass, TimeFrame
)
from aegis_trade.engine.events import MarketEvent, SignalEvent, SignalIntent
from aegis_trade.strategies.composite_macro import CompositeMacroStrategy

def test_composite_macro_strategy_long_signal_accepted():
    ts = datetime(2024, 7, 25, 19, 0, tzinfo=timezone.utc)
    # EMA Cross (fast < slow to fast > slow) will trigger LONG
    # DXY Trend Baissier (-1) -> Accepts LONG
    strategy = CompositeMacroStrategy(symbol="XAUUSD", fast_period=2, slow_period=3, macro_data={ts: -1})
    
    # Need to feed enough bars for EMA Cross to trigger.
    # We will simulate the cross by feeding prices.
    
    bar1 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10"), Decimal("100"))
    bar2 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10"), Decimal("100"))
    bar3 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10"), Decimal("100"))
    bar4 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("20"), Decimal("20"), Decimal("20"), Decimal("20"), Decimal("100"))
    
    strategy.on_market_event(MarketEvent(bar=bar1, timestamp=ts))
    strategy.on_market_event(MarketEvent(bar=bar2, timestamp=ts))
    strategy.on_market_event(MarketEvent(bar=bar3, timestamp=ts))
    signals = strategy.on_market_event(MarketEvent(bar=bar4, timestamp=ts))
    
    assert len(signals) == 1
    assert signals[0].intent == SignalIntent.ENTER_LONG

def test_composite_macro_strategy_long_signal_rejected():
    ts = datetime(2024, 7, 25, 19, 0, tzinfo=timezone.utc)
    # EMA Cross will trigger LONG
    # DXY Trend Haussier (1) -> Rejects LONG
    strategy = CompositeMacroStrategy(symbol="XAUUSD", fast_period=2, slow_period=3, macro_data={ts: 1})
    
    bar1 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10"), Decimal("100"))
    bar2 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10"), Decimal("100"))
    bar3 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10"), Decimal("100"))
    bar4 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("20"), Decimal("20"), Decimal("20"), Decimal("20"), Decimal("100"))
    
    strategy.on_market_event(MarketEvent(bar=bar1, timestamp=ts))
    strategy.on_market_event(MarketEvent(bar=bar2, timestamp=ts))
    strategy.on_market_event(MarketEvent(bar=bar3, timestamp=ts))
    signals = strategy.on_market_event(MarketEvent(bar=bar4, timestamp=ts))
    
    assert len(signals) == 0

def test_composite_macro_strategy_short_signal_accepted():
    ts = datetime(2024, 7, 25, 19, 0, tzinfo=timezone.utc)
    # EMA Cross will trigger SHORT
    # DXY Trend Haussier (1) -> Accepts SHORT
    strategy = CompositeMacroStrategy(symbol="XAUUSD", fast_period=2, slow_period=3, macro_data={ts: 1})
    
    bar1 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("20"), Decimal("20"), Decimal("20"), Decimal("20"), Decimal("100"))
    bar2 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("20"), Decimal("20"), Decimal("20"), Decimal("20"), Decimal("100"))
    bar3 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("20"), Decimal("20"), Decimal("20"), Decimal("20"), Decimal("100"))
    bar4 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10"), Decimal("100"))
    
    strategy.on_market_event(MarketEvent(bar=bar1, timestamp=ts))
    strategy.on_market_event(MarketEvent(bar=bar2, timestamp=ts))
    strategy.on_market_event(MarketEvent(bar=bar3, timestamp=ts))
    signals = strategy.on_market_event(MarketEvent(bar=bar4, timestamp=ts))
    
    assert len(signals) == 1
    assert signals[0].intent == SignalIntent.ENTER_SHORT

def test_composite_macro_strategy_short_signal_rejected():
    ts = datetime(2024, 7, 25, 19, 0, tzinfo=timezone.utc)
    # EMA Cross will trigger SHORT
    # DXY Trend Baissier (-1) -> Rejects SHORT
    strategy = CompositeMacroStrategy(symbol="XAUUSD", fast_period=2, slow_period=3, macro_data={ts: -1})
    
    bar1 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("20"), Decimal("20"), Decimal("20"), Decimal("20"), Decimal("100"))
    bar2 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("20"), Decimal("20"), Decimal("20"), Decimal("20"), Decimal("100"))
    bar3 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("20"), Decimal("20"), Decimal("20"), Decimal("20"), Decimal("100"))
    bar4 = MarketBar(Symbol("XAUUSD", AssetClass.FOREX), TimeFrame.H1, ts, Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10"), Decimal("100"))
    
    strategy.on_market_event(MarketEvent(bar=bar1, timestamp=ts))
    strategy.on_market_event(MarketEvent(bar=bar2, timestamp=ts))
    strategy.on_market_event(MarketEvent(bar=bar3, timestamp=ts))
    signals = strategy.on_market_event(MarketEvent(bar=bar4, timestamp=ts))
    
    assert len(signals) == 0
