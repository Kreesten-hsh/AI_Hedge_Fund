from abc import ABC, abstractmethod
from datetime import datetime
from typing import Sequence

from aegis_trade.domain.core import (
    Symbol,
    TimeFrame,
    MarketBar,
    EconomicIndicator,
    MarketSnapshot,
    NewsItem
)

class IDataProvider(ABC):
    """
    Port for data providers.
    All implementations must return domain objects, never DataFrames.
    """

    @abstractmethod
    def fetch_ohlcv(
        self, symbol: Symbol, timeframe: TimeFrame, start: datetime, end: datetime
    ) -> Sequence[MarketBar]:
        """Fetch historical price and volume data."""
        pass

    @abstractmethod
    def fetch_macro(
        self, symbol: Symbol, start: datetime, end: datetime
    ) -> Sequence[EconomicIndicator]:
        """Fetch macroeconomic indicators."""
        pass

    @abstractmethod
    def fetch_snapshot(self, symbol: Symbol) -> MarketSnapshot:
        """Fetch the latest available snapshot for a symbol."""
        pass

    @abstractmethod
    def fetch_news(self, symbol: Symbol, start: datetime, end: datetime) -> Sequence[NewsItem]:
        """Fetch relevant news items."""
        pass
