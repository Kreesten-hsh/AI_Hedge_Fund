from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from decimal import Decimal
import time
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.api.deps import get_dashboard_service, get_orchestrator
from aegis_trade.api.security import require_api_token
from aegis_trade.domain.core import Symbol
from aegis_trade.engine.events import OrderAction, OrderEvent
from aegis_trade.engine.risk_gate import OrderRejectedByRisk

router = APIRouter()

@router.get("")
def get_positions(service: DashboardService = Depends(get_dashboard_service)):
    return list(service.monitoring.positions.values())

@router.get("/open")
def get_open_positions(service: DashboardService = Depends(get_dashboard_service)):
    return list(service.monitoring.positions.values())

@router.post("/{symbol}/close", dependencies=[Depends(require_api_token)])
async def close_position(
    symbol: str,
    service: DashboardService = Depends(get_dashboard_service),
    orchestrator = Depends(get_orchestrator)
):
    positions = service.monitoring.positions
    if symbol not in positions:
        raise HTTPException(status_code=404, detail="Position not found")

    pos = positions[symbol]
    action = OrderAction.SELL if pos.side == "LONG" else OrderAction.BUY

    order_event = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        symbol=Symbol(name=symbol, asset_class="forex"),
        action=action,
        volume=Decimal(str(pos.quantity)),
        order_type="market",
        strategy_id="api_manual_close",
    )

    order_id = f"CLOSE-{int(time.time())}"
    try:
        # Passe par le RiskEngine comme tout autre ordre : aucune route API ne
        # parle au broker en direct.
        await orchestrator.submit_order(
            order_event,
            latest_prices={order_event.symbol: Decimal(str(pos.current_price))},
            order_id=order_id,
        )
    except OrderRejectedByRisk as rejection:
        raise HTTPException(status_code=409, detail=rejection.reason)

    return {"status": "closing", "symbol": symbol, "order_id": order_id}
