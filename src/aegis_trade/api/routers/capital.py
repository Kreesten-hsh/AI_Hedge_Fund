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
    # Assuming GlobalRiskManager has capital_allocation or similar mechanism.
    # We will build a representation based on the real GlobalRiskManager.
    risk_manager = orchestrator.risk_manager
    
    # In the current implementation of GlobalRiskManager, it uses a simpler model
    # Let's map its state to a tier representation for the dashboard
    
    # Placeholder mapping based on standard Risk Manager attributes
    tiers = []
    
    # Mocking standard tiers if not natively supported in GlobalRiskManager yet
    # Or using its real attributes if available
    tiers.append(CapitalTierModel(
        name="Tier 1 (Base)",
        max_drawdown_limit=float(risk_manager.max_drawdown),
        current_drawdown=0.0, # Would be calculated from PortfolioEngine
        equity_allocated=float(orchestrator.portfolio_engine.initial_capital),
        is_active=True
    ))
    
    return tiers
