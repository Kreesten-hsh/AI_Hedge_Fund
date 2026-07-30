from fastapi import APIRouter, Depends
from aegis_trade.api.deps import get_orchestrator
from aegis_trade.application.paper_trading.orchestrator import PaperTradingOrchestrator
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

router = APIRouter()

class AgentVoteModel(BaseModel):
    agent_name: str
    direction: str
    confidence: float

class CouncilVerdictModel(BaseModel):
    final_vote: str
    aggregated_confidence: float
    position_size_multiplier: float
    votes: List[AgentVoteModel]
    veto_reason: Optional[str] = None
    disagreement_level: float

class RLPolicyModel(BaseModel):
    risk_multiplier: float
    confidence_threshold_adjustment: float
    agent_weights: Dict[str, float]

class CouncilStatusResponse(BaseModel):
    verdict: Optional[CouncilVerdictModel] = None
    policy: Optional[RLPolicyModel] = None

@router.get("/latest", response_model=CouncilStatusResponse)
def get_latest_council_decision(
    orchestrator: PaperTradingOrchestrator = Depends(get_orchestrator)
):
    """Returns the latest council verdict and RL policy."""
    response = CouncilStatusResponse()
    
    if orchestrator.latest_verdict:
        response.verdict = CouncilVerdictModel(
            final_vote=orchestrator.latest_verdict.final_vote,
            aggregated_confidence=orchestrator.latest_verdict.aggregated_confidence,
            position_size_multiplier=orchestrator.latest_verdict.position_size_multiplier,
            votes=[
                AgentVoteModel(
                    agent_name=v.agent_name,
                    direction=v.direction,
                    confidence=v.confidence
                ) for v in orchestrator.latest_verdict.votes
            ],
            veto_reason=orchestrator.latest_verdict.veto_reason,
            disagreement_level=orchestrator.latest_verdict.disagreement_level
        )
        
    if orchestrator.latest_policy:
        response.policy = RLPolicyModel(
            risk_multiplier=orchestrator.latest_policy.risk_multiplier,
            confidence_threshold_adjustment=orchestrator.latest_policy.confidence_threshold_adjustment,
            agent_weights=orchestrator.latest_policy.agent_weights
        )
        
    return response
