import pytest
from decimal import Decimal
from datetime import datetime, timezone

from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.infrastructure.risk.global_risk_adapter import GlobalRiskAdapter
from aegis_trade.domain.execution import OrderIntent
from aegis_trade.domain.core import Symbol, AssetClass

def test_global_risk_adapter_approval():
    rm = GlobalRiskManager(max_drawdown=Decimal("0.05"))
    adapter = GlobalRiskAdapter(rm)
    
    intent = OrderIntent(
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        direction=1,
        quantity=10,
        target_price=100.0,
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc)
    )
    
    is_appr, msg = adapter.validate_intent(
        intent=intent,
        current_capital=10000.0,
        initial_capital=10000.0,
        equity_curve={datetime(2023,1,1, tzinfo=timezone.utc): 10000.0},
        current_position=0.0
    )
    
    assert is_appr is True
    assert msg == ""

def test_global_risk_adapter_rejection_drawdown():
    rm = GlobalRiskManager(max_drawdown=Decimal("0.05"))
    adapter = GlobalRiskAdapter(rm)
    
    intent = OrderIntent(
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        direction=1,
        quantity=10,
        target_price=100.0,
        timestamp=datetime(2023, 1, 2, tzinfo=timezone.utc)
    )
    
    is_appr, msg = adapter.validate_intent(
        intent=intent,
        current_capital=9400.0,
        initial_capital=10000.0,
        equity_curve={
            datetime(2023,1,1, tzinfo=timezone.utc): 10000.0,
            datetime(2023,1,2, tzinfo=timezone.utc): 9400.0
        },
        current_position=0.0
    )
    
    assert is_appr is False
    assert "Kill Switch activated" in msg
