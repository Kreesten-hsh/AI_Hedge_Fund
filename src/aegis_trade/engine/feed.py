from abc import ABC, abstractmethod
from typing import Iterator

from aegis_trade.dataset.domain import Dataset
from aegis_trade.dataset.resolver import DatasetResolver
from aegis_trade.engine.events import MarketEvent


class MarketDataFeed(ABC):
    """
    Interface for a Market Data Feed.
    Yields MarketEvents chronologically.
    """
    @abstractmethod
    def __iter__(self) -> Iterator[MarketEvent]:
        pass


class HistoricalReplayFeed(MarketDataFeed):
    """
    Simulates a live market feed by replaying historical data.
    """
    def __init__(self, dataset: Dataset, resolver: DatasetResolver, start_idx: int = 0, end_idx: int | None = None):
        self._dataset = dataset
        self._resolver = resolver
        self._start_idx = start_idx
        self._end_idx = end_idx

    def __iter__(self) -> Iterator[MarketEvent]:
        bars = self._resolver.load_data(self._dataset)
        if self._end_idx is not None:
            bars = bars[self._start_idx:self._end_idx]
        else:
            bars = bars[self._start_idx:]
            
        for bar in bars:
            yield MarketEvent(timestamp=bar.timestamp, bar=bar)
