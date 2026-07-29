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
    # Only 100 USD in account
    account = PaperAccount(
        account_id="A1", 
        balances={"USD": PaperBalance("USD", Decimal("100.0"), Decimal("0.0"), Decimal("100.0"))}
    )
    
    async def dummy_publisher(event):
        pass
        
    return PaperBroker(
        account=account,
        slippage_model=ConstantSlippageModel(Decimal("0.0")),
        latency_model=ConstantLatencyModel(0.0),
        commission_model=FixedCommissionModel(Decimal("0.0")),
        repository=MemoryExecutionRepository(),
        event_publisher=dummy_publisher
    )

@pytest.mark.asyncio
async def test_insufficient_funds(broker):
    order = PaperOrder(
        order_id="O1",
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=ActionType.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("10.0"),
        timestamp=datetime.now(timezone.utc)
    )
    
    broker.update_market_price(Decimal("150.0")) # Needs 1500 USD, has 100 USD
    report = await broker.submit_order(order)
    
    assert report.order.state == OrderState.REJECTED
    assert "Insufficient funds" in report.risk_decision

@pytest.mark.asyncio
async def test_invalid_order_state(broker):
    order = PaperOrder(
        order_id="O1",
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=ActionType.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("10.0"),
        timestamp=datetime.now(timezone.utc),
        state=OrderState.FILLED # Already filled!
    )
    
    report = await broker.submit_order(order)
    assert report.order.state == OrderState.REJECTED
    assert "Invalid state transition" in report.risk_decision
