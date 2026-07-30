from fastapi import APIRouter, Depends
from aegis_trade.api.deps import get_monitoring_engine
from aegis_trade.application.monitoring.engine import MonitoringEngine
from aegis_trade.domain.reasoning import KnowledgeType
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter()

class KnowledgeScoreModel(BaseModel):
    confidence: float
    support: int
    frequency: float
    stability: float
    recency: float

class KnowledgeModel(BaseModel):
    id: str
    type: str
    description: str
    features_conditions: Dict[str, Dict[str, float]]
    score: KnowledgeScoreModel

@router.get("/rules", response_model=List[KnowledgeModel])
def get_knowledge_rules(
    monitoring: MonitoringEngine = Depends(get_monitoring_engine)
):
    """Returns the active rules discovered by the Reasoning Engine."""
    if not monitoring.knowledge_repo:
        return []
        
    active_knowledge = monitoring.knowledge_repo.get_all_active()
    
    response = []
    for k in active_knowledge:
        response.append(KnowledgeModel(
            id=k.id,
            type=k.type.value,
            description=k.description,
            features_conditions=k.features_conditions,
            score=KnowledgeScoreModel(
                confidence=k.score.confidence,
                support=k.score.support,
                frequency=k.score.frequency,
                stability=k.score.stability,
                recency=k.score.recency
            )
        ))
        
    return response
