from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote
from typing import Optional
from aegis_trade.domain.forecasting import IForecaster

class TrendAgent:
    """
    Analyzes medium-term market structure (Trend).
    Uses EMA or SMA features.
    """
    def __init__(self, forecaster: Optional[IForecaster] = None):
        self.forecaster = forecaster

    @property
    def name(self) -> str:
        return "TrendAgent"

    def vote(self, context: MarketContext) -> AgentVote:
        current_price = context.latest_prices.get(context.symbol)
        if current_price is None:
            return AgentVote(self.name, "WAIT", 0.0)

        # Naive implementation assuming 'ema_50' is provided in features
        ema = context.features.get('ema_50')
        if ema is None:
            return AgentVote(self.name, "WAIT", 0.0)

        price_f = float(current_price)
        base_decision = "WAIT"
        base_conf = 0.2
        
        if price_f > ema * 1.001:  # 0.1% buffer
            base_decision = "BUY"
            base_conf = 0.7
        elif price_f < ema * 0.999:
            base_decision = "SELL"
            base_conf = 0.7
            
        base_vote = AgentVote(self.name, base_decision, base_conf)
        
        # -------------------------------------------------------------
        # Kronos Integration (Fallback & Non-regression)
        # -------------------------------------------------------------
        if not self.forecaster:
            return base_vote
            
        forecast = self.forecaster.get_latest_forecast(context.symbol)
        if not forecast or not forecast.predicted_values:
            return base_vote
            
        avg_pred = sum(forecast.predicted_values) / len(forecast.predicted_values)
        
        # Simple heuristic: if predicted avg is higher than current price -> bullish
        forecast_is_bullish = avg_pred > price_f
        
        if base_decision == "BUY" and forecast_is_bullish:
            return AgentVote(self.name, "BUY", min(base_conf + 0.15, 1.0))
        elif base_decision == "SELL" and not forecast_is_bullish:
            return AgentVote(self.name, "SELL", min(base_conf + 0.15, 1.0))
        elif base_decision != "WAIT":
            # Disagreement between Trend and Kronos prediction
            reduced_conf = max(base_conf - 0.20, 0.0)
            if reduced_conf < 0.2:
                return AgentVote(self.name, "WAIT", 0.0)
            return AgentVote(self.name, base_decision, reduced_conf)
            
        return base_vote
