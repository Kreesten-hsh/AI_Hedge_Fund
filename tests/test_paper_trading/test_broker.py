import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from aegis_trade.domain import Symbol, AssetClass
from aegis_trade.domain.paper.models import PaperOrder, OrderType, ActionType, OrderState, PaperAccount, PaperBalance
from aegis_trade.infrastructure.paper.models import ConstantSlippageModel, ConstantLatencyModel, FixedCommissionModel
from aegis_trade.infrastructure.paper.repositories import MemoryExecutionRepository
from aegis_trade.infrastructure.paper.broker import PaperBroker

@pytest.fixture
def broker():
    account = PaperAccount(
        account_id="A1", 
        balances={"USD": PaperBalance("USD", Decimal("10000.0"), Decimal("0.0"), Decimal("10000.0"))}
    )
    
    events = []
    async def dummy_publisher(event):
        events.append(event)
        
    brk = PaperBroker(
        account=account,
        slippage_model=ConstantSlippageModel(Decimal("0.0")),
        latency_model=ConstantLatencyModel(0.0),
        commission_model=FixedCommissionModel(Decimal("0.0")),
        repository=MemoryExecutionRepository(),
        event_publisher=dummy_publisher
    )
    brk.published_events = events
    return brk


@pytest.mark.asyncio
async def test_successful_buy_order(broker):
    order = PaperOrder(
        order_id="O1",
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=ActionType.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("10.0"),
        timestamp=datetime.now(timezone.utc)
    )
    
    broker.update_market_price(Decimal("150.0"))
    report = await broker.submit_order(order)
    
    # Assert Order State
    assert report.order.state == OrderState.FILLED
    assert report.order.filled_volume == Decimal("10.0")
    
    # Assert Balances
    assert broker.account.balances["USD"].total == Decimal("10000.0") - Decimal("1500.0")
    assert Symbol("AAPL", AssetClass.EQUITIES) in broker.account.positions
    assert broker.account.positions[Symbol("AAPL", AssetClass.EQUITIES)].volume == Decimal("10.0")
    
    # Assert Events emitted
    statuses = [e.status for e in broker.published_events if hasattr(e, 'status')]
    assert "submitted" in statuses
    assert "accepted" in statuses
    assert "filled" in statuses
