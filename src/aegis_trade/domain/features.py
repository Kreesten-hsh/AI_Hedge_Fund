from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any

from aegis_trade.domain.core import Symbol, TimeFrame

class FeatureGroup(str, Enum):
    RETURNS = "returns"
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    PRICE = "price"

@dataclass(frozen=True, slots=True)
class FeatureMetadata:
    name: str
    description: str
    group: FeatureGroup
    parameters: Dict[str, Any]

@dataclass(frozen=True, slots=True)
class FeatureSet:
    symbol: Symbol
    timeframe: TimeFrame
    timestamp: datetime
    features: Dict[str, float]

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo != timezone.utc:
            raise ValueError("FeatureSet timestamp must be UTC.")
