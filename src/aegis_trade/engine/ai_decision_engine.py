import json
import collections
from decimal import Decimal
from typing import Optional, List

from aegis_trade.engine.risk import RiskEngine
from aegis_trade.engine.events import SignalEvent, OrderEvent, OrderAction, SignalIntent, MarketEvent
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.agents.council import CouncilOrchestrator

class AiDecisionEngine(RiskEngine):
    """
    AI-driven Risk Engine.
    Intercepts signals, fetches AI consensus via CouncilOrchestrator, 
    and applies AI multiplier to standard position sizing.
    """
    def __init__(self, orchestrator: CouncilOrchestrator, risk_pct: Decimal = Decimal("0.10"), window_size: int = 5):
        self._orchestrator = orchestrator
        self._risk_pct = risk_pct
        self._window_size = window_size
        self._history = collections.deque(maxlen=window_size)
        
    def on_market_event(self, event: MarketEvent) -> None:
        """Stores the latest market events to build context."""
        self._history.append(event.bar)

    def on_signal_event(self, event: SignalEvent, portfolio: Portfolio) -> list[OrderEvent]:
        # Only process entry signals for AI (exits are standard)
        if event.intent not in (SignalIntent.ENTER_LONG, SignalIntent.ENTER_SHORT):
            return self._handle_exit(event, portfolio)
            
        current_pos = portfolio.get_position(event.symbol)
        latest_price = portfolio.get_latest_price(event.symbol)
        
        if latest_price is None or latest_price <= 0:
            return []

        # Wait until we have enough history
        if len(self._history) < self._window_size:
            return []
            
        # 1. Build Context for the Council
        # Simplistic extraction of recent price action
        recent_price_action = [
            {"timestamp": str(bar.timestamp), "close": float(bar.close)}
            for bar in self._history
        ]
        
        # Calculate a mock ATR over the window
        atr_mock = float(sum((bar.high - bar.low) for bar in self._history) / len(self._history))
        
        # In a real system, you'd merge DXY and US10Y data here. 
        # For simulation, we provide neutral placeholders.
        context = {
            "recent_price_action": json.dumps(recent_price_action),
            "dxy_trend_filter": 0,
            "current_price": float(latest_price),
            "volatility": f"{atr_mock:.2f}",
            "drawdown": "0.0%",
            "dxy_trend": "Neutral",
            "us10y_trend": "Neutral",
            "atr": atr_mock,
            "avg_atr": atr_mock,
            "volatility_regime": "normal"
        }
        
        intent_str = "LONG" if event.intent == SignalIntent.ENTER_LONG else "SHORT"
        
        # 2. Ask Council
        decision = self._orchestrator.generate_decision(context, intent=intent_str)
        
        # 3. Apply Decision
        if decision.decision_type in ("reject", "wait") or decision.multiplier <= 0:
            return [] # Signal cancelled
            
        # 4. Standard Sizing * AI Multiplier
        base_volume = (portfolio.equity * self._risk_pct) / latest_price
        target_volume = base_volume * Decimal(str(decision.multiplier))
        target_volume = round(target_volume, 2)
        
        if target_volume <= 0:
            return []
            
        orders = []
        
        if event.intent == SignalIntent.ENTER_LONG:
            if current_pos is None:
                orders.append(self._create_order(event, OrderAction.BUY, target_volume))
            elif current_pos.volume < 0:
                orders.append(self._create_order(event, OrderAction.BUY, abs(current_pos.volume))) # Close short
                orders.append(self._create_order(event, OrderAction.BUY, target_volume)) # Open long
        elif event.intent == SignalIntent.ENTER_SHORT:
            if current_pos is None:
                orders.append(self._create_order(event, OrderAction.SELL, target_volume))
            elif current_pos.volume > 0:
                orders.append(self._create_order(event, OrderAction.SELL, current_pos.volume)) # Close long
                orders.append(self._create_order(event, OrderAction.SELL, target_volume)) # Open short
                
        return orders
        
    def _handle_exit(self, event: SignalEvent, portfolio: Portfolio) -> list[OrderEvent]:
        current_pos = portfolio.get_position(event.symbol)
        orders = []
        if event.intent == SignalIntent.EXIT_LONG and current_pos is not None and current_pos.volume > 0:
            orders.append(self._create_order(event, OrderAction.SELL, current_pos.volume))
        elif event.intent == SignalIntent.EXIT_SHORT and current_pos is not None and current_pos.volume < 0:
            orders.append(self._create_order(event, OrderAction.BUY, abs(current_pos.volume)))
        return orders
        
    def _create_order(self, event: SignalEvent, action: OrderAction, volume: Decimal) -> OrderEvent:
        return OrderEvent(
            timestamp=event.timestamp,
            symbol=event.symbol,
            action=action,
            volume=volume,
            strategy_id=f"{event.strategy_id}_AI"
        )
