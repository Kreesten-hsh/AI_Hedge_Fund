from abc import ABC, abstractmethod
from decimal import Decimal

from aegis_trade.engine.events import MarketEvent, SignalEvent, SignalIntent


class Strategy(ABC):
    """
    Interface for an Event-Driven Strategy.
    """
    @property
    @abstractmethod
    def strategy_id(self) -> str:
        pass

    @abstractmethod
    def on_market_event(self, event: MarketEvent) -> list[SignalEvent]:
        """
        Consumes a MarketEvent and optionally produces a list of SignalEvents.
        """
        pass


class EmaCrossStrategy(Strategy):
    """
    Exponential Moving Average Crossover Strategy for Pipeline Validation.
    """
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._fast_ema: Decimal | None = None
        self._slow_ema: Decimal | None = None
        self._prev_fast_ema: Decimal | None = None
        self._prev_slow_ema: Decimal | None = None
        self._observations = 0

    @property
    def strategy_id(self) -> str:
        return "ema_cross_v1"

    def on_market_event(self, event: MarketEvent) -> list[SignalEvent]:
        price = event.bar.close
        
        # Calculate fast EMA
        if self._fast_ema is None:
            self._fast_ema = price
        else:
            multiplier = Decimal("2") / Decimal(self._fast_period + 1)
            self._fast_ema = ((price - self._fast_ema) * multiplier) + self._fast_ema
            
        # Calculate slow EMA
        if self._slow_ema is None:
            self._slow_ema = price
        else:
            multiplier = Decimal("2") / Decimal(self._slow_period + 1)
            self._slow_ema = ((price - self._slow_ema) * multiplier) + self._slow_ema
            
        self._observations += 1
        signals = []

        if self._observations > self._slow_period and self._prev_fast_ema is not None and self._prev_slow_ema is not None:
            # Bullish Cross
            if self._prev_fast_ema <= self._prev_slow_ema and self._fast_ema > self._slow_ema:
                signals.append(SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.bar.symbol,
                    intent=SignalIntent.ENTER_LONG,
                    strategy_id=self.strategy_id
                ))
            # Bearish Cross
            elif self._prev_fast_ema >= self._prev_slow_ema and self._fast_ema < self._slow_ema:
                signals.append(SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.bar.symbol,
                    intent=SignalIntent.ENTER_SHORT,
                    strategy_id=self.strategy_id
                ))

        self._prev_fast_ema = self._fast_ema
        self._prev_slow_ema = self._slow_ema

        return signals

class RsiEmaStrategy(Strategy):
    """
    RSI + EMA Crossover Strategy for Pipeline Validation.
    Uses EMA crossover for trend direction, filtered by RSI for momentum confirmation.
    """
    def __init__(self, fast_period: int = 20, slow_period: int = 50, rsi_period: int = 14):
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._rsi_period = rsi_period
        self._fast_ema: Decimal | None = None
        self._slow_ema: Decimal | None = None
        self._prev_fast_ema: Decimal | None = None
        self._prev_slow_ema: Decimal | None = None
        
        self._prev_price: Decimal | None = None
        self._avg_gain: Decimal | None = None
        self._avg_loss: Decimal | None = None
        self._observations = 0

    @property
    def strategy_id(self) -> str:
        return "rsi_ema_v1"

    def on_market_event(self, event: MarketEvent) -> list[SignalEvent]:
        price = event.bar.close
        
        # Calculate EMA
        if self._fast_ema is None:
            self._fast_ema = price
            self._slow_ema = price
        else:
            self._fast_ema = ((price - self._fast_ema) * (Decimal("2") / Decimal(self._fast_period + 1))) + self._fast_ema
            self._slow_ema = ((price - self._slow_ema) * (Decimal("2") / Decimal(self._slow_period + 1))) + self._slow_ema
            
        # Calculate RSI
        rsi_value = Decimal("50")
        if self._prev_price is not None:
            delta = price - self._prev_price
            gain = delta if delta > 0 else Decimal("0")
            loss = -delta if delta < 0 else Decimal("0")
            
            if self._avg_gain is None:
                self._avg_gain = gain
                self._avg_loss = loss
            else:
                self._avg_gain = (self._avg_gain * Decimal(self._rsi_period - 1) + gain) / Decimal(self._rsi_period)
                self._avg_loss = (self._avg_loss * Decimal(self._rsi_period - 1) + loss) / Decimal(self._rsi_period)
                
            if self._avg_loss == Decimal("0"):
                rsi_value = Decimal("100")
            else:
                rs = self._avg_gain / self._avg_loss
                rsi_value = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))
                
        self._prev_price = price
        self._observations += 1
        signals = []

        if self._observations > max(self._slow_period, self._rsi_period) and self._prev_fast_ema is not None and self._prev_slow_ema is not None:
            # Bullish Cross and RSI > 50 (Momentum up)
            if self._prev_fast_ema <= self._prev_slow_ema and self._fast_ema > self._slow_ema and rsi_value > Decimal("50"):
                signals.append(SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.bar.symbol,
                    intent=SignalIntent.ENTER_LONG,
                    strategy_id=self.strategy_id
                ))
            # Bearish Cross and RSI < 50 (Momentum down)
            elif self._prev_fast_ema >= self._prev_slow_ema and self._fast_ema < self._slow_ema and rsi_value < Decimal("50"):
                signals.append(SignalEvent(
                    timestamp=event.timestamp,
                    symbol=event.bar.symbol,
                    intent=SignalIntent.ENTER_SHORT,
                    strategy_id=self.strategy_id
                ))

        self._prev_fast_ema = self._fast_ema
        self._prev_slow_ema = self._slow_ema

        return signals

class BuyAndHoldStrategy(Strategy):
    """
    Buy and Hold Strategy. Emits a single LONG signal on the first bar.
    """
    def __init__(self):
        self._has_entered = False

    @property
    def strategy_id(self) -> str:
        return "buy_and_hold_v1"

    def on_market_event(self, event: MarketEvent) -> list[SignalEvent]:
        if not self._has_entered:
            self._has_entered = True
            return [SignalEvent(
                timestamp=event.timestamp,
                symbol=event.bar.symbol,
                intent=SignalIntent.ENTER_LONG,
                strategy_id=self.strategy_id
            )]
        return []

class Return5MomentumStrategy(Strategy):
    """
    Momentum Strategy based on Return5 feature.
    Goes LONG if Return5 > 0, SHORT if Return5 < 0, HOLD if 0.
    """
    def __init__(self):
        self._lookback_closes: list[Decimal] = []
        self._current_intent: SignalIntent | None = None

    @property
    def strategy_id(self) -> str:
        return "return5_momentum_v1"

    def on_market_event(self, event: MarketEvent) -> list[SignalEvent]:
        price = event.bar.close
        self._lookback_closes.append(price)

        if len(self._lookback_closes) > 6:
            self._lookback_closes.pop(0)

        # We need at least 6 prices (t and t-5)
        if len(self._lookback_closes) == 6:
            price_t = self._lookback_closes[-1]
            price_t5 = self._lookback_closes[0]
            
            if price_t5 > 0:
                return5 = (price_t - price_t5) / price_t5
                
                intent = None
                if return5 > 0:
                    intent = SignalIntent.ENTER_LONG
                elif return5 < 0:
                    intent = SignalIntent.ENTER_SHORT
                    
                if intent is not None and intent != self._current_intent:
                    self._current_intent = intent
                    return [SignalEvent(
                        timestamp=event.timestamp,
                        symbol=event.bar.symbol,
                        intent=intent,
                        strategy_id=self.strategy_id
                    )]
        
        return []

