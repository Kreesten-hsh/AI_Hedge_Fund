import json
import collections
from decimal import Decimal
from typing import Optional, List

import numpy as np

from aegis_trade.engine.risk import RiskEngine
from aegis_trade.engine.events import SignalEvent, OrderEvent, OrderAction, SignalIntent, MarketEvent
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.domain.council import MarketContext
from aegis_trade.domain.core import MarketBar
from aegis_trade.utils.math import compute_atr

# Wilder a besoin de `period + 1` barres pour produire une première valeur non
# NaN. En deçà, l'ATR n'existe pas et le contexte du Council doit le dire
# plutôt que de servir un nombre calculé sur un échantillon incomplet.
ATR_PERIOD = 14

class AiDecisionEngine(RiskEngine):
    """
    AI-driven Risk Engine.
    Intercepts signals, evaluates deterministic MultiAgentCouncil, 
    and applies Council position size multiplier to standard position sizing.
    """
    def __init__(self, council: MultiAgentCouncil, risk_pct: Decimal = Decimal("0.10"), window_size: int = 5):
        self._council = council
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

        # 1. Build MarketContext for MultiAgentCouncil
        current_bar = self._history[-1]
        features = {
            "close": float(current_bar.close),
            "volume": float(current_bar.volume),
            "atr": current_atr,
            "avg_atr": avg_atr,
        }

        context = MarketContext(
            symbol=event.symbol,
            features=features,
            portfolio=portfolio,
            latest_prices={event.symbol: latest_price},
            memory_score=0.0,
        )
        
        # 2. Evaluate Council Verdict
        verdict = self._council.evaluate(context)
        
        # 3. Apply Decision
        if verdict.final_vote == "WAIT" or verdict.position_size_multiplier <= 0:
            return [] # Signal cancelled
            
        # 4. Standard Sizing * AI Multiplier
        base_volume = (portfolio.equity * self._risk_pct) / latest_price
        target_volume = base_volume * Decimal(str(verdict.position_size_multiplier))
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
