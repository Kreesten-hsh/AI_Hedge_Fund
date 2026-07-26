from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar, Optional

from aegis_trade.domain import Symbol, TimeFrame

T = TypeVar('T')

@dataclass(frozen=True)
class Dataset(Generic[T]):
    dataset_hash: str
    symbol: Symbol
    timeframe: Optional[TimeFrame]
    row_count: int
    date_start: datetime
    date_end: datetime


@dataclass(frozen=True)
class DatasetMetadata:
    dataset_hash: str
    provider: str
    provider_version: str
    validator_version: str
    builder_version: str
    schema_version: str = "1.0"
