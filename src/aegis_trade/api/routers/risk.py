from fastapi import APIRouter, Depends
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.application.monitoring.models import RiskSnapshot
from aegis_trade.api.deps import get_dashboard_service

router = APIRouter()

@router.get("", response_model=RiskSnapshot)
def get_risk_status(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_risk_status()

@router.post("/kill-switch")
async def trigger_kill_switch(service: DashboardService = Depends(get_dashboard_service)):
    # Simulates publishing an emergency event to the EventBus
    service.monitoring.risk.risk_status = "HALTED"
    service.monitoring.risk.global_exposure = 0
    if service.monitoring.system.strategy_status:
        service.monitoring.system.strategy_status.status = "Stopped"
        
    # Broadcast the new state to all connected WebSocket clients
    await service.monitoring._broadcast("risk", service.monitoring.risk)
    await service.monitoring._broadcast("system", service.monitoring.system)
    
    return {"status": "KILL_SWITCH_ENGAGED", "message": "Liquidating all positions and cancelling orders"}
