from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote
from aegis_trade.infrastructure.reasoning.knowledge_repo import IKnowledgeRepository
from aegis_trade.domain.reasoning import KnowledgeType
from typing import Optional
from aegis_trade.domain.forecasting import IForecaster

class PatternAgent:
    """
    Vector analysis and predictive projection.
    Uses FAISS Success/Failure Memory (represented here by memory_score).
    Score is between -100 and +100.
    """
    def __init__(self, knowledge_repo: IKnowledgeRepository = None, forecaster: Optional[IForecaster] = None):
        self.knowledge_repo = knowledge_repo
        self.forecaster = forecaster

    @property
    def name(self) -> str:
        return "PatternAgent"

    def vote(self, context: MarketContext) -> AgentVote:
        score = context.memory_score
        
        # Adjust score based on actual knowledge if repo is available
        if self.knowledge_repo:
            active_knowledge = self.knowledge_repo.get_all_active()
            for k in active_knowledge:
                # Naive matching: if memory_score > 0 and we have preferred patterns, boost score
                # A real implementation would compare MarketContext features with k.features_conditions
                if k.type == KnowledgeType.PREFERRED_PATTERN and score > 0:
                    score = min(score + 10.0, 100.0)
                elif k.type == KnowledgeType.AVOID_PATTERN and score < 0:
                    score = max(score - 10.0, -100.0)
        
        if score == 0.0:
            base_vote = AgentVote(self.name, "WAIT", 0.0)
        else:
            confidence = min(abs(score) / 100.0, 1.0)
            if score > 0:
                base_vote = AgentVote(self.name, "BUY", confidence)
            else:
                base_vote = AgentVote(self.name, "SELL", confidence)
                
        # -------------------------------------------------------------
        # Kronos Integration (Fallback & Non-regression)
        # -------------------------------------------------------------
        if not self.forecaster:
            return base_vote
            
        forecast = self.forecaster.get_latest_forecast(context.symbol)
        if not forecast or not forecast.predicted_values:
            return base_vote
            
        current_price = context.latest_prices.get(context.symbol)
        if current_price is None:
            return base_vote
            
        avg_pred = sum(forecast.predicted_values) / len(forecast.predicted_values)
        forecast_is_bullish = avg_pred > float(current_price)
        
        if base_vote.vote == "BUY" and forecast_is_bullish:
            return AgentVote(self.name, "BUY", min(base_vote.confidence + 0.1, 1.0))
        elif base_vote.vote == "SELL" and not forecast_is_bullish:
            return AgentVote(self.name, "SELL", min(base_vote.confidence + 0.1, 1.0))
        elif base_vote.vote != "WAIT":
            reduced_conf = max(base_vote.confidence - 0.15, 0.0)
            if reduced_conf < 0.2:
                return AgentVote(self.name, "WAIT", 0.0)
            return AgentVote(self.name, base_vote.vote, reduced_conf)
            
        return base_vote
