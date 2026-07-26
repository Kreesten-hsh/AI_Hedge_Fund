from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.domain import Symbol, AssetClass, MarketBar, TimeFrame
from aegis_trade.engine.events import MarketEvent, SignalIntent
from aegis_trade.engine.strategy import RsiEmaStrategy

def test_rsi_filter_blocks_signal_when_rsi_low():
    """
    Forces an EMA cross UP while RSI is forced to be LOW (< 50).
    Verifies that the strategy does NOT emit a signal.
    """
    strategy = RsiEmaStrategy(fast_period=3, slow_period=5, rsi_period=14)
    symbol = Symbol("TEST", AssetClass.FOREX)
    
    # We want fast_ema to cross slow_ema UP, but RSI to be < 50.
    # RSI < 50 means average loss > average gain over 14 periods.
    # We can achieve this by having a long slow downtrend, followed by a massive single upward gap
    # that is enough to pull the fast EMA above the slow EMA, but maybe the 14-period avg loss is still huge?
    # Wait, if there's a massive gap up, avg gain spikes, making RSI > 50.
    # How to make fast EMA > slow EMA without making RSI > 50?
    # Let's just manually feed prices.
    
    # Let's do a sequence that produces the exact state we want.
    # Or, we can just manipulate the strategy's internal state for a pure unit test.
    
    strategy._observations = 100
    strategy._prev_fast_ema = Decimal("100")
    strategy._prev_slow_ema = Decimal("105")  # Currently fast is below slow
    
    # Now we simulate a new bar that crosses them, but keeps RSI low.
    # We can just set the EMA state explicitly before the last on_market_event.
    # But on_market_event calculates EMA from the price.
    # Let's set fast_ema and slow_ema directly to almost crossing, then feed a price that crosses.
    strategy._fast_ema = Decimal("100")
    strategy._slow_ema = Decimal("105")
    
    # Set RSI internal state to have huge losses and tiny gains
    strategy._avg_gain = Decimal("1")
    strategy._avg_loss = Decimal("10")
    strategy._prev_price = Decimal("100")
    
    # Now feed a price of 115.
    # Fast EMA (alpha = 2/4 = 0.5): (115 - 100) * 0.5 + 100 = 107.5
    # Slow EMA (alpha = 2/6 = 0.333): (115 - 105) * 0.333 + 105 = 108.33 (still hasn't crossed)
    
    # Let's use a bigger price: 150
    # Fast: (150-100)*0.5 + 100 = 125
    # Slow: (150-105)*0.333 + 105 = 120
    # CROSS UP!
    
    # What about RSI on price = 150?
    # prev_price = 100. Gain = 50.
    # avg_gain = (1 * 13 + 50) / 14 = 63 / 14 = 4.5
    # avg_loss = (10 * 13 + 0) / 14 = 130 / 14 = 9.28
    # rs = 4.5 / 9.28 = 0.48
    # rsi = 100 - (100 / 1.48) = 100 - 67.5 = 32.5
    
    # RSI is 32.5 (< 50)!
    # Fast crossed above Slow!
    # Let's run it.
    
    bar = MarketBar(
        symbol=symbol,
        timeframe=TimeFrame.M5,
        timestamp=datetime.now(timezone.utc),
        open=Decimal("150"),
        high=Decimal("150"),
        low=Decimal("150"),
        close=Decimal("150"),
        volume=Decimal("100")
    )
    
    event = MarketEvent(timestamp=bar.timestamp, bar=bar)
    signals = strategy.on_market_event(event)
    
    assert len(signals) == 0, "Signal should be blocked by RSI < 50 filter!"
    print("Test passed: RSI filter successfully blocked the EMA cross!")

if __name__ == "__main__":
    test_rsi_filter_blocks_signal_when_rsi_low()
