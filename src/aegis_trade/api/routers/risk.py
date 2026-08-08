from fastapi import APIRouter, Depends
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.application.monitoring.models import RiskSnapshot
from aegis_trade.api.deps import get_dashboard_service, get_orchestrator
from aegis_trade.api.security import require_api_token
from aegis_trade.application.paper_trading.orchestrator import PaperTradingOrchestrator

router = APIRouter()

@router.get("", response_model=RiskSnapshot)
def get_risk_status(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_risk_status()

@router.post("/kill-switch", dependencies=[Depends(require_api_token)])
async def trigger_kill_switch(
    service: DashboardService = Depends(get_dashboard_service),
    orchestrator: PaperTradingOrchestrator = Depends(get_orchestrator)
):
    # Call real emergency halt
    halt_result = await orchestrator.risk_manager.emergency_halt(gateway=orchestrator.broker)
    
    # Update dashboard state
    service.monitoring.risk.risk_status = "HALTED"
    service.monitoring.risk.global_exposure = 0
    if service.monitoring.system.strategy_status:
        service.monitoring.system.strategy_status.status = "Stopped"
        
    # Broadcast the new state to all connected WebSocket clients
    await service.monitoring._broadcast("risk", service.monitoring.risk)
    await service.monitoring._broadcast("system", service.monitoring.system)
    
    return {
        "status": "KILL_SWITCH_ENGAGED", 
        "message": "Liquidating all positions and cancelling orders",
        "details": halt_result
    }
