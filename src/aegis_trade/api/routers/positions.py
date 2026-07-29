from fastapi import APIRouter, Depends
from typing import List, Dict
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.application.monitoring.models import PositionSnapshot
from aegis_trade.api.deps import get_dashboard_service

router = APIRouter()

@router.get("")
def get_positions(service: DashboardService = Depends(get_dashboard_service)):
    return list(service.monitoring.positions.values())

@router.get("/open")
def get_open_positions(service: DashboardService = Depends(get_dashboard_service)):
    return list(service.monitoring.positions.values())
