import pytest
from datetime import datetime, timezone
from decimal import Decimal
from aegis_trade.domain import Symbol, AssetClass
from aegis_trade.domain.paper.models import PaperOrder, OrderType, OrderState, ActionType

def test_paper_order_initial_state():
    order = PaperOrder(
        order_id="1",
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=ActionType.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("10.0"),
        timestamp=datetime.now(timezone.utc)
    )
    assert order.state == OrderState.CREATED

def test_valid_state_transitions():
    order = PaperOrder(
        order_id="1",
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=ActionType.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("10.0"),
        timestamp=datetime.now(timezone.utc)
    )
    
    assert order.can_transition_to(OrderState.SUBMITTED) is True
    assert order.can_transition_to(OrderState.FILLED) is False

def test_invalid_state_transitions():
    order = PaperOrder(
        order_id="1",
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=ActionType.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("10.0"),
        timestamp=datetime.now(timezone.utc),
        state=OrderState.FILLED
    )
    
    # Un ordre FILLED ne peut aller nulle part.
    assert order.can_transition_to(OrderState.CANCELLED) is False
    assert order.can_transition_to(OrderState.REJECTED) is False
