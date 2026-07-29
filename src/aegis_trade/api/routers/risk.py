from fastapi import APIRouter, Depends
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.application.monitoring.models import RiskSnapshot
from aegis_trade.api.deps import get_dashboard_service

router = APIRouter()

@router.get("", response_model=RiskSnapshot)
def get_risk_status(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_risk_status()

@router.post("/kill-switch")
def trigger_kill_switch(service: DashboardService = Depends(get_dashboard_service)):
    # This would publish an emergency event to the engine
    return {"status": "KILL_SWITCH_ENGAGED", "message": "Liquidating all positions and cancelling orders"}
