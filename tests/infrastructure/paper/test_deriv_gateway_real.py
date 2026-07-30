import pytest
import os
from unittest.mock import patch
from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.infrastructure.paper.deriv_gateway import DerivGateway, LiveDerivGateway, SecurityError
from aegis_trade.domain.core import Symbol, AssetClass
from aegis_trade.domain.paper.models import PaperOrder, ActionType, OrderType

@pytest.mark.anyio
async def test_deriv_gateway_rejects_submit_without_virtual_confirmation():
    gateway = DerivGateway(token="demo_token_123")
    # Simulate API object existing but virtual confirmation skipped
    gateway.api = object() 
    gateway._is_virtual_confirmed = False
    
    order = PaperOrder(
        order_id="1",
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=ActionType.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("1.0"),
        timestamp=datetime.now(timezone.utc)
    )
    
    with pytest.raises(SecurityError) as exc:
        await gateway.submit_order(order)
    
    assert "Attempted to submit order without virtual account confirmation" in str(exc.value)

def test_live_gateway_refuses_without_explicit_live_flag():
    # Correct environment but missing consent flag
    with patch.dict(os.environ, {"AEGIS_ENV": "LIVE"}):
        with pytest.raises(SecurityError) as exc:
            LiveDerivGateway(token="real_token", i_understand_this_is_real_money=False)
        assert "Explicit consent required" in str(exc.value)

def test_live_gateway_refuses_wrong_environment():
    # Consent flag given but wrong environment
    with patch.dict(os.environ, {"AEGIS_ENV": "DEV"}):
        with pytest.raises(SecurityError) as exc:
            LiveDerivGateway(token="real_token", i_understand_this_is_real_money=True)
        assert "can ONLY be used in LIVE environment" in str(exc.value)

def test_live_gateway_initializes_correctly():
    # Both correct
    with patch.dict(os.environ, {"AEGIS_ENV": "LIVE"}):
        gateway = LiveDerivGateway(token="real_token", i_understand_this_is_real_money=True)
        assert gateway.token == "real_token"
        assert gateway._is_virtual_confirmed is False # Wait for connect()
