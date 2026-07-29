from typing import List, Dict, Tuple
from aegis_trade.domain.council import AgentVote

class VoteAggregator:
    """
    Aggregates votes using RL-provided weights.
    If no weights provided, defaults to equal weights.
    """
    def __init__(self, agent_weights: Dict[str, float] = None):
        self.agent_weights = agent_weights or {}

    def _get_weight(self, agent_name: str, total_agents: int) -> float:
        """Returns the specific weight from PolicyDecision or a default equal weight."""
        if agent_name in self.agent_weights:
            return self.agent_weights[agent_name]
        # Default fallback: equal weighting if not specified by RL policy
        return 1.0 / total_agents if total_agents > 0 else 1.0

    def aggregate(self, votes: List[AgentVote]) -> Tuple[str, float, float, float]:
        """
        Aggregates the votes and returns:
        (final_vote, aggregated_confidence, buy_score, sell_score)
        """
        if not votes:
            return "WAIT", 0.0, 0.0, 0.0

        total_agents = len(votes)
        buy_score = 0.0
        sell_score = 0.0
        
        # Normalize weights to sum to 1.0 for the agents that actually voted
        raw_weights = {v.agent_name: self._get_weight(v.agent_name, total_agents) for v in votes}
        total_weight = sum(raw_weights.values())
        if total_weight == 0:
            total_weight = 1.0
            
        normalized_weights = {k: v / total_weight for k, v in raw_weights.items()}

        for vote in votes:
            weight = normalized_weights[vote.agent_name]
            score = vote.confidence * weight
            
            if vote.vote == "BUY":
                buy_score += score
            elif vote.vote == "SELL":
                sell_score += score

        if buy_score > sell_score and buy_score > 0.0:
            return "BUY", buy_score, buy_score, sell_score
        elif sell_score > buy_score and sell_score > 0.0:
            return "SELL", sell_score, buy_score, sell_score
            
        return "WAIT", 0.0, buy_score, sell_score
