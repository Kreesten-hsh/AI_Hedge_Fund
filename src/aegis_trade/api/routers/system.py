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
