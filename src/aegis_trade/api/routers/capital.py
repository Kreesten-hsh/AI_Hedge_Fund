from fastapi import APIRouter, Depends
from aegis_trade.api.deps import get_orchestrator
from aegis_trade.application.paper_trading.orchestrator import PaperTradingOrchestrator
from pydantic import BaseModel
from typing import List
from decimal import Decimal

router = APIRouter()

class CapitalTierModel(BaseModel):
    name: str
    max_drawdown_limit: float
    current_drawdown: float
    equity_allocated: float
    is_active: bool

@router.get("/tiers", response_model=List[CapitalTierModel])
def get_capital_tiers(
    orchestrator: PaperTradingOrchestrator = Depends(get_orchestrator)
):
    """Returns the current capital tiers from the GlobalRiskManager."""
    risk_manager = orchestrator.risk_manager
    allocation = getattr(risk_manager, "capital_allocation", None)
    
    if not allocation:
        return []
        
    tiers = []
    for tier in allocation.tiers:
        current_drawdown = float(tier.high_water_mark - tier.current_equity)
        max_drawdown = float(tier.max_drawdown_amount)
        
        tiers.append(CapitalTierModel(
            name=tier.tier_id,
            max_drawdown_limit=max_drawdown,
            current_drawdown=current_drawdown,
            equity_allocated=float(tier.current_equity),
            is_active=tier.is_active
        ))
        
    return tiers
