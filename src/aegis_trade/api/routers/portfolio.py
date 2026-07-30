from fastapi import APIRouter, Depends
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.application.monitoring.models import PortfolioSnapshot
from aegis_trade.api.deps import get_dashboard_service

router = APIRouter()

@router.get("", response_model=PortfolioSnapshot)
def get_portfolio(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_portfolio_status()

@router.get("/history")
def get_portfolio_history(range: str = "1d", service: DashboardService = Depends(get_dashboard_service)):
    if range == "1h":
        return service.monitoring.history_1h
    elif range == "1d":
        return service.monitoring.history_1d
    elif range == "7d":
        # we might not have 7d yet, return whatever we have or fallback to 1d
        return service.monitoring.history_1d
    else:
        return service.monitoring.history_1m
