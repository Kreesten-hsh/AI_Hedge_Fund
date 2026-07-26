from datetime import datetime
from typing import Dict
from aegis_trade.engine.strategy import Strategy
from aegis_trade.engine.events import MarketEvent, SignalEvent, SignalIntent

class MacroDxyStrategy(Strategy):
    """
    Macro DXY Momentum Strategy.
    Generates signals based on the 5-day momentum of the DXY.
    If DXY Mom5 > 0 => LONG XAUUSD.
    If DXY Mom5 < 0 => SHORT XAUUSD.
    """

    def __init__(self, symbol: str = "XAUUSD", macro_data: Dict[datetime, float] = None):
        self.symbol = symbol
        self.macro_data = macro_data or {}
        
    @property
    def strategy_id(self) -> str:
        return "MacroDxy_1.0"

    def on_market_event(self, event: MarketEvent) -> list[SignalEvent]:
        signals = []
        bar = event.bar
        
        if bar.symbol.name != self.symbol:
            return signals

        # Lookup dxy_mom5 from the pre-computed macro_data dictionary
        dxy_mom5 = self.macro_data.get(bar.timestamp, None)
        
        if dxy_mom5 is None:
            return signals

        if dxy_mom5 > 0:
            signals.append(SignalEvent(
                timestamp=event.timestamp,
                symbol=bar.symbol,
                intent=SignalIntent.ENTER_LONG,
                strategy_id=self.strategy_id
            ))
        elif dxy_mom5 < 0:
            signals.append(SignalEvent(
                timestamp=event.timestamp,
                symbol=bar.symbol,
                intent=SignalIntent.ENTER_SHORT,
                strategy_id=self.strategy_id
            ))
            
        return signals
