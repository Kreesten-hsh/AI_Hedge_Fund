from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

@dataclass
class CapitalTier:
    tier_id: str
    allocated_amount: Decimal
    max_drawdown_amount: Decimal
    current_equity: Decimal = field(init=False)
    high_water_mark: Decimal = field(init=False)
    is_active: bool = True
    
    def __post_init__(self):
        self.current_equity = self.allocated_amount
        self.high_water_mark = self.allocated_amount
        
    def update_equity(self, new_equity: Decimal):
        """Updates equity and checks the kill switch."""
        if not self.is_active:
            return
            
        self.current_equity = new_equity
        if self.current_equity > self.high_water_mark:
            self.high_water_mark = self.current_equity
            
        absolute_drawdown = self.high_water_mark - self.current_equity
        if absolute_drawdown >= self.max_drawdown_amount:
            self.is_active = False

@dataclass
class CapitalAllocation:
    tiers: List[CapitalTier]
    
    def get_tier(self, tier_id: str) -> Optional[CapitalTier]:
        for tier in self.tiers:
            if tier.tier_id == tier_id:
                return tier
        return None
        
    def get_total_active_equity(self) -> Decimal:
        return sum(t.current_equity for t in self.tiers if t.is_active)
        
    def get_total_allocated(self) -> Decimal:
        return sum(t.allocated_amount for t in self.tiers)
