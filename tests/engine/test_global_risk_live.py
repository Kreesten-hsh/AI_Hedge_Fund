import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.domain.capital import CapitalAllocation, CapitalTier
from aegis_trade.domain.core import Symbol, AssetClass
from aegis_trade.engine.events import OrderEvent, OrderAction

def test_global_risk_manager_stricter_in_live_mode():
    # In live mode, we just pass stricter configs
    risk_manager = GlobalRiskManager(
        max_drawdown=Decimal("0.02") # 2% vs 5% default
    )
    assert risk_manager.max_drawdown == Decimal("0.02")

def test_global_risk_manager_blocks_if_allocation_killed():
    tier1 = CapitalTier(tier_id="T1", allocated_amount=Decimal("50.0"), max_drawdown_amount=Decimal("5.0"))
    allocation = CapitalAllocation(tiers=[tier1])
    
    risk_manager = GlobalRiskManager(capital_allocation=allocation)
    
    portfolio = MagicMock()
    portfolio.equity = Decimal("44.0") # We dropped 6.0, which > 5.0
    tier1.update_equity(portfolio.equity)
    
    assert tier1.is_active is False
    
    from datetime import datetime, timezone
    order = OrderEvent(
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=OrderAction.BUY,
        volume=Decimal("1.0"),
        timestamp=datetime.now(timezone.utc)
    )
    
    passed, reason = risk_manager.validate_order(order, portfolio, {Symbol("AAPL", AssetClass.EQUITIES): Decimal("100.0")})
    assert passed is False
    assert "All tiers are killed" in reason
