from fastapi import APIRouter, Depends
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.application.monitoring.models import PortfolioSnapshot
from aegis_trade.api.deps import get_dashboard_service

router = APIRouter()

@router.get("", response_model=PortfolioSnapshot)
def get_portfolio(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_portfolio_status()

@router.get("/history")
def get_portfolio_history(service: DashboardService = Depends(get_dashboard_service)):
    return {"history_1m": service.monitoring.history_1m}
