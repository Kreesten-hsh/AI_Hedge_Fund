from fastapi import APIRouter, Depends
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.application.monitoring.models import SystemSnapshot
from aegis_trade.api.deps import get_dashboard_service, get_orchestrator
from aegis_trade.api.security import require_api_token
from aegis_trade.application.paper_trading.orchestrator import PaperTradingOrchestrator

router = APIRouter()

@router.get("/")
def get_system_info():
    return {"version": "1.0.0", "status": "online"}

@router.get("/health", response_model=SystemSnapshot)
def get_system_health(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_system_health()

@router.post("/strategy/{strategy_id}/start", dependencies=[Depends(require_api_token)])
async def start_strategy(
    strategy_id: str,
    service: DashboardService = Depends(get_dashboard_service),
    orchestrator: PaperTradingOrchestrator = Depends(get_orchestrator)
):
    await orchestrator.start()
    
    if service.monitoring.system.strategy_status:
        service.monitoring.system.strategy_status.status = "Live"
        await service.monitoring._broadcast("system", service.monitoring.system)
    return {"status": "SUCCESS", "message": f"Strategy {strategy_id} started (Orchestrator task running)"}

@router.post("/strategy/{strategy_id}/stop", dependencies=[Depends(require_api_token)])
async def stop_strategy(
    strategy_id: str,
    service: DashboardService = Depends(get_dashboard_service),
    orchestrator: PaperTradingOrchestrator = Depends(get_orchestrator)
):
    await orchestrator.stop()
    
    if service.monitoring.system.strategy_status:
        service.monitoring.system.strategy_status.status = "Stopped"
        await service.monitoring._broadcast("system", service.monitoring.system)
    return {"status": "SUCCESS", "message": f"Strategy {strategy_id} stopped (Orchestrator task cancelled)"}
