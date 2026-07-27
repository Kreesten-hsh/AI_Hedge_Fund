from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from decimal import Decimal

class ValidationCampaignType(str, Enum):
    WALK_FORWARD = "walk_forward"
    HOLD_OUT = "hold_out"
    MULTI_MARKET = "multi_market"
    MULTI_TIMEFRAME = "multi_timeframe"
    MONTE_CARLO = "monte_carlo"
    BENCHMARK = "benchmark"

@dataclass(frozen=True, slots=True)
class ValidationContext:
    seed: int
    git_version: str
    strategy_version: str
    config_version: str
    data_hash: str
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo != timezone.utc:
            raise ValueError("ValidationContext timestamp must be UTC.")

@dataclass(frozen=True, slots=True)
class ValidationCampaignResult:
    campaign_type: ValidationCampaignType
    metrics: Dict[str, float]
    passed: bool
    details: Dict[str, Any]

@dataclass(frozen=True, slots=True)
class ValidationReport:
    campaigns: List[ValidationCampaignResult]
    strategy_score: float
    is_approved: bool

    def __post_init__(self) -> None:
        if not (0.0 <= self.strategy_score <= 100.0):
            raise ValueError("Strategy score must be between 0 and 100.")

@dataclass(frozen=True, slots=True)
class ValidationArtifact:
    context: ValidationContext
    report: ValidationReport
    parameters: Dict[str, Any]
