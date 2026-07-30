from aegis_trade.domain.council import IVotingAgent, MarketContext, AgentVote
from aegis_trade.infrastructure.reasoning.knowledge_repo import IKnowledgeRepository
from aegis_trade.domain.reasoning import KnowledgeType

class PatternAgent:
    """
    Vector analysis and predictive projection.
    Uses FAISS Success/Failure Memory (represented here by memory_score).
    Score is between -100 and +100.
    """
    def __init__(self, knowledge_repo: IKnowledgeRepository = None):
        self.knowledge_repo = knowledge_repo

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
            return AgentVote(self.name, "WAIT", 0.0)
            
        confidence = min(abs(score) / 100.0, 1.0)
        
        if score > 0:
            return AgentVote(self.name, "BUY", confidence)
        else:
            return AgentVote(self.name, "SELL", confidence)
