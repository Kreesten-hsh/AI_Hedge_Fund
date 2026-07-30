import pytest
from decimal import Decimal
from aegis_trade.domain.capital import CapitalTier, CapitalAllocation

def test_capital_tier_kills_switch_on_drawdown():
    tier = CapitalTier(tier_id="T1", allocated_amount=Decimal("50.0"), max_drawdown_amount=Decimal("5.0"))
    assert tier.is_active is True
    
    tier.update_equity(Decimal("48.0")) # 2.0 drawdown
    assert tier.is_active is True
    
    tier.update_equity(Decimal("51.0")) # new HWM
    assert tier.high_water_mark == Decimal("51.0")
    
    tier.update_equity(Decimal("46.0")) # 5.0 drawdown from 51.0
    assert tier.is_active is False

def test_capital_allocation_isolates_tiers():
    tier1 = CapitalTier(tier_id="T1", allocated_amount=Decimal("50.0"), max_drawdown_amount=Decimal("5.0"))
    tier2 = CapitalTier(tier_id="T2", allocated_amount=Decimal("50.0"), max_drawdown_amount=Decimal("5.0"))
    
    allocation = CapitalAllocation(tiers=[tier1, tier2])
    assert allocation.get_total_active_equity() == Decimal("100.0")
    
    tier1.update_equity(Decimal("45.0")) # kills tier1
    assert tier1.is_active is False
    assert tier2.is_active is True # tier2 is isolated
    
    assert allocation.get_total_active_equity() == Decimal("50.0") # only tier2 is active
