import json
import collections
from decimal import Decimal
from typing import Optional, List

import numpy as np

from aegis_trade.engine.risk import RiskEngine
from aegis_trade.engine.events import SignalEvent, OrderEvent, OrderAction, SignalIntent, MarketEvent
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.agents.council import CouncilOrchestrator
from aegis_trade.domain.core import MarketBar
from aegis_trade.utils.math import compute_atr

# Wilder a besoin de `period + 1` barres pour produire une première valeur non
# NaN. En deçà, l'ATR n'existe pas et le contexte du Council doit le dire
# plutôt que de servir un nombre calculé sur un échantillon incomplet.
ATR_PERIOD = 14

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
        # L'historique doit couvrir l'ATR, pas seulement la fenêtre de contexte :
        # `2 * ATR_PERIOD` laisse assez de valeurs non-NaN pour que `avg_atr`
        # soit une vraie moyenne et non une recopie de l'ATR courant.
        self._history: collections.deque[MarketBar] = collections.deque(
            maxlen=max(window_size, 2 * ATR_PERIOD)
        )

    def on_market_event(self, event: MarketEvent) -> None:
        """Stores the latest market events to build context."""
        self._history.append(event.bar)

    def _atr_stats(self) -> tuple[float, float] | None:
        """ATR courant et moyenne historique, ou None si l'historique est trop court.

        Délègue à `utils.math.compute_atr` — autorité numérique unique du projet.
        Remplace un `mean(high - low)` qui ignorait les gaps entre barres et
        sous-estimait la volatilité de ~9,5 % contre la référence Wilder.
        """
        if len(self._history) < ATR_PERIOD + 1:
            return None
        bars = list(self._history)
        atr_series = compute_atr(
            np.array([float(b.high) for b in bars]),
            np.array([float(b.low) for b in bars]),
            np.array([float(b.close) for b in bars]),
            ATR_PERIOD,
        )
        valid = atr_series[~np.isnan(atr_series)]
        if valid.size == 0:
            return None
        return float(valid[-1]), float(valid.mean())

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

        # Un moteur de risque ne demande pas au Council de dimensionner une
        # position quand la volatilité n'est pas encore calculable. Refuser est
        # honnête ; fabriquer un ATR ne l'est pas.
        atr_stats = self._atr_stats()
        if atr_stats is None:
            return []
        current_atr, avg_atr = atr_stats

        # 1. Build Context for the Council
        # Simplistic extraction of recent price action
        recent_price_action = [
            {"timestamp": str(bar.timestamp), "close": float(bar.close)}
            for bar in list(self._history)[-self._window_size:]
        ]

        # In a real system, you'd merge DXY and US10Y data here.
        # For simulation, we provide neutral placeholders.
        context = {
            "recent_price_action": json.dumps(recent_price_action),
            "dxy_trend_filter": 0,
            "current_price": float(latest_price),
            "volatility": f"{current_atr:.2f}",
            "drawdown": "0.0%",
            "dxy_trend": "Neutral",
            "us10y_trend": "Neutral",
            "atr": current_atr,
            "avg_atr": avg_atr,
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
