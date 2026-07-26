from decimal import Decimal

from aegis_trade.engine.strategy import Strategy
from aegis_trade.engine.events import MarketEvent, SignalEvent, SignalIntent

class EmaCrossStrategy(Strategy):
    """
    Simple EMA Cross strategy (Base signal).
    """

    def __init__(self, symbol: str = "XAUUSD", fast_period: int = 20, slow_period: int = 50):
        self.symbol = symbol
        self.fast_period = fast_period
        self.slow_period = slow_period
        
        self._fast_ema: Decimal | None = None
        self._slow_ema: Decimal | None = None
        self._prev_fast_ema: Decimal | None = None
        self._prev_slow_ema: Decimal | None = None
        self._observations = 0

    @property
    def strategy_id(self) -> str:
        return "ema_cross_v1"

    def on_market_event(self, event: MarketEvent) -> list[SignalEvent]:
        signals = []
        bar = event.bar
        
        if bar.symbol.name != self.symbol:
            return signals

        price = bar.close
        
        # Calculate fast EMA
        if self._fast_ema is None:
            self._fast_ema = price
        else:
            multiplier = Decimal("2") / Decimal(self.fast_period + 1)
            self._fast_ema = ((price - self._fast_ema) * multiplier) + self._fast_ema
            
        # Calculate slow EMA
        if self._slow_ema is None:
            self._slow_ema = price
        else:
            multiplier = Decimal("2") / Decimal(self.slow_period + 1)
            self._slow_ema = ((price - self._slow_ema) * multiplier) + self._slow_ema
            
        self._observations += 1

        if self._observations > self.slow_period and self._prev_fast_ema is not None and self._prev_slow_ema is not None:
            bullish_cross = self._prev_fast_ema <= self._prev_slow_ema and self._fast_ema > self._slow_ema
            bearish_cross = self._prev_fast_ema >= self._prev_slow_ema and self._fast_ema < self._slow_ema
            
            if bullish_cross:
                signals.append(SignalEvent(
                    timestamp=event.timestamp,
                    symbol=bar.symbol,
                    intent=SignalIntent.ENTER_LONG,
                    strategy_id=self.strategy_id
                ))
            elif bearish_cross:
                signals.append(SignalEvent(
                    timestamp=event.timestamp,
                    symbol=bar.symbol,
                    intent=SignalIntent.ENTER_SHORT,
                    strategy_id=self.strategy_id
                ))

        self._prev_fast_ema = self._fast_ema
        self._prev_slow_ema = self._slow_ema

        return signals
