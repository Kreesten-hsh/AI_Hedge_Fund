from abc import ABC, abstractmethod
from typing import Iterator

from aegis_trade.domain.core import Symbol, TimeFrame
from aegis_trade.domain.features import FeatureSet

class IDataFeed(ABC):
    """
    Port for sequential data feeds used in backtesting.
    """
    @abstractmethod
    def get_feature_stream(self, symbol: Symbol, timeframe: TimeFrame) -> Iterator[FeatureSet]:
        """
        Yields FeatureSets sequentially for a given symbol and timeframe.
        """
        pass
