import time
import logging
from typing import List, Dict, Optional
from aegis_trade.domain.council import IVotingAgent, MarketContext, CouncilVerdict
from aegis_trade.domain.rl import PolicyDecision
from aegis_trade.application.council.vote_aggregator import VoteAggregator
from aegis_trade.application.council.conflict_resolver import ConflictResolver
from aegis_trade.engine.events import OrderEvent, OrderAction
from aegis_trade.domain import Symbol

logger = logging.getLogger(__name__)

class MultiAgentCouncil:
    """
    Orchestrates the 8 voting agents, aggregates their votes, resolves conflicts,
    and produces a final deterministic CouncilVerdict.
    """
    def __init__(self, agents: List[IVotingAgent], max_latency_ms: float = 20.0):
        self.agents = agents
        self.max_latency_ms = max_latency_ms
        self.conflict_resolver = ConflictResolver()

    def evaluate(self, context: MarketContext, policy: Optional[PolicyDecision] = None) -> CouncilVerdict:
        """
        Runs the council vote.
        Enforces latency budget guard.
        """
        start_time = time.perf_counter()
        
        # 1. Collect votes
        votes = []
        for agent in self.agents:
            vote = agent.vote(context)
            votes.append(vote)
            
        # 2. Aggregation
        # Extract weights from RL Policy (AI-04), default to empty if no policy
        weights = policy.agent_weights if policy else {}
        aggregator = VoteAggregator(agent_weights=weights)
        final_vote, agg_confidence, buy_score, sell_score = aggregator.aggregate(votes)
        
        # 3. Conflict Resolution
        size_multiplier, disagreement = self.conflict_resolver.resolve(buy_score, sell_score)
        
        # 4. Apply RL Policy Risk Multipliers (AI-04)
        if policy:
            size_multiplier *= policy.risk_multiplier
            # If confidence is below the RL-adjusted threshold, we veto
            base_threshold = 0.5
            adjusted_threshold = base_threshold + policy.confidence_threshold_adjustment
            if agg_confidence < adjusted_threshold:
                final_vote = "WAIT"
                
        # If conflict resolver completely aborted
        if size_multiplier <= 0.0:
            final_vote = "WAIT"

        # 5. Latency Guard
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if elapsed_ms > self.max_latency_ms:
            logger.warning(f"Council Latency Guard breached: {elapsed_ms:.2f}ms > {self.max_latency_ms}ms")
            
        return CouncilVerdict(
            final_vote=final_vote,
            aggregated_confidence=agg_confidence,
            position_size_multiplier=size_multiplier,
            votes=votes,
            veto_reason=None if final_vote != "WAIT" else "Confidence too low or high disagreement",
            disagreement_level=disagreement
        )

    def create_order(self, verdict: CouncilVerdict, symbol: Symbol, base_volume: float, context: Optional[MarketContext] = None) -> Optional[OrderEvent]:
        """
        Transforms a successful verdict into an OrderEvent (ready to be routed to GlobalRiskManager).
        """
        if verdict.final_vote == "WAIT" or verdict.position_size_multiplier <= 0:
            return None
            
        from decimal import Decimal
        action = OrderAction.BUY if verdict.final_vote == "BUY" else OrderAction.SELL
        final_volume = Decimal(str(base_volume * verdict.position_size_multiplier))
        
        from datetime import datetime, timezone
        return OrderEvent(
            symbol=symbol,
            action=action,
            volume=final_volume,
            order_type="MARKET",
            timestamp=datetime.now(timezone.utc),
            context_features=context.features if context else {}
        )
