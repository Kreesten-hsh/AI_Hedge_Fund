from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from datetime import datetime, timezone
import time
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.application.monitoring.models import PositionSnapshot
from aegis_trade.api.deps import get_dashboard_service, get_orchestrator
from aegis_trade.domain.paper.models import PaperOrder, OrderType, ActionType
from aegis_trade.domain.core import Symbol

router = APIRouter()

@router.get("")
def get_positions(service: DashboardService = Depends(get_dashboard_service)):
    return list(service.monitoring.positions.values())

@router.get("/open")
def get_open_positions(service: DashboardService = Depends(get_dashboard_service)):
    return list(service.monitoring.positions.values())

@router.post("/{symbol}/close")
async def close_position(
    symbol: str, 
    service: DashboardService = Depends(get_dashboard_service),
    orchestrator = Depends(get_orchestrator)
):
    positions = service.monitoring.positions
    if symbol not in positions:
        raise HTTPException(status_code=404, detail="Position not found")
        
    pos = positions[symbol]
    action = ActionType.SELL if pos.side == "LONG" else ActionType.BUY
    
    paper_order = PaperOrder(
        order_id=f"CLOSE-{int(time.time())}",
        symbol=Symbol(name=symbol, asset_class="forex"),
        action=action,
        order_type=OrderType.MARKET,
        volume=pos.quantity,
        timestamp=datetime.now(timezone.utc)
    )
    
    await orchestrator.broker.submit_order(paper_order)
    return {"status": "closing", "symbol": symbol, "order_id": paper_order.order_id}
