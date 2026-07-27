from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from aegis_trade.domain.core import Symbol, TimeFrame
from aegis_trade.domain.validation import ValidationCampaignType

@dataclass(frozen=True)
class ValidationConfig:
    """
    Objet de configuration centralisant le paramétrage des campagnes de validation.
    """
    # Active campaigns
    active_campaigns: List[ValidationCampaignType] = field(default_factory=lambda: [
        ValidationCampaignType.WALK_FORWARD,
        ValidationCampaignType.HOLD_OUT,
        ValidationCampaignType.MONTE_CARLO,
        ValidationCampaignType.BENCHMARK
    ])
    
    # Global parameters
    seed: int = 42
    
    # Time splits (for Walk-Forward / Hold-Out)
    train_ratio: float = 0.6
    val_ratio: float = 0.2
    test_ratio: float = 0.2
    
    # Monte Carlo specifics
    monte_carlo_iterations: int = 10000
    monte_carlo_level: int = 1 # 1: bootstrap, 2: noise, 3: stress
    
    # Multi-market targets
    markets: List[Symbol] = field(default_factory=list)
    
    # Multi-timeframe targets
    timeframes: List[TimeFrame] = field(default_factory=list)
    
    # Benchmarks to run
    benchmarks: List[str] = field(default_factory=lambda: ["buy_and_hold", "random"])
    
    def is_active(self, campaign: ValidationCampaignType) -> bool:
        return campaign in self.active_campaigns
