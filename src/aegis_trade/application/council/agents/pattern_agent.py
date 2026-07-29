from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote

class PatternAgent:
    """
    Vector analysis and predictive projection.
    Uses FAISS Success/Failure Memory (represented here by memory_score).
    Score is between -100 and +100.
    """
    @property
    def name(self) -> str:
        return "PatternAgent"

    def vote(self, context: MarketContext) -> AgentVote:
        score = context.memory_score
        
        if score == 0.0:
            return AgentVote(self.name, "WAIT", 0.0)
            
        confidence = min(abs(score) / 100.0, 1.0)
        
        if score > 0:
            return AgentVote(self.name, "BUY", confidence)
        else:
            return AgentVote(self.name, "SELL", confidence)
