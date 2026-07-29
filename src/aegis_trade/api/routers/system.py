from fastapi import APIRouter, Depends
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.application.monitoring.models import SystemSnapshot
from aegis_trade.api.deps import get_dashboard_service

router = APIRouter()

@router.get("/")
def get_system_info():
    return {"version": "1.0.0", "status": "online"}

@router.get("/health", response_model=SystemSnapshot)
def get_system_health(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_system_health()

@router.post("/strategy/{strategy_id}/start")
async def start_strategy(strategy_id: str, service: DashboardService = Depends(get_dashboard_service)):
    if service.monitoring.system.strategy_status:
        service.monitoring.system.strategy_status.status = "Live"
        await service.monitoring._broadcast("system", service.monitoring.system)
    return {"status": "SUCCESS", "message": f"Strategy {strategy_id} started"}

@router.post("/strategy/{strategy_id}/stop")
async def stop_strategy(strategy_id: str, service: DashboardService = Depends(get_dashboard_service)):
    if service.monitoring.system.strategy_status:
        service.monitoring.system.strategy_status.status = "Stopped"
        await service.monitoring._broadcast("system", service.monitoring.system)
    return {"status": "SUCCESS", "message": f"Strategy {strategy_id} stopped"}
