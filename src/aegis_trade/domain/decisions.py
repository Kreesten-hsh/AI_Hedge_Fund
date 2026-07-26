from dataclasses import dataclass
from typing import Dict, Any, List
from aegis_trade.domain.reports import ResearchReport

@dataclass(frozen=True)
class CouncilDecision:
    """Domain object representing the final synthetic decision of the Council."""
    decision_type: str  # e.g., "go_long", "go_short", "reduce_risk", "wait", "reject"
    confidence: float
    multiplier: float
    reasoning: str
    supporting_reports: List[ResearchReport]
