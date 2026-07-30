from fastapi import APIRouter, Depends
from typing import List, Dict
from datetime import datetime, timezone

from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.api.deps import get_dashboard_service
from aegis_trade.domain.trade_record import TradeRecord

router = APIRouter()

@router.get("", response_model=List[TradeRecord])
def get_trades(service: DashboardService = Depends(get_dashboard_service)):
    """Get the full history of executed trades."""
    # In a full implementation, this might support pagination and filters
    return service.monitoring.get_trades()

@router.get("/today/count", response_model=Dict[str, int])
def get_today_trades_count(service: DashboardService = Depends(get_dashboard_service)):
    """Get the number of trades closed today (UTC)."""
    trades = service.monitoring.get_trades()
    today = datetime.now(timezone.utc).date()
    count = sum(1 for t in trades if t.close_timestamp.date() == today)
    return {"count": count}
