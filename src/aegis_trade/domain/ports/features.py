import abc
from typing import List, Sequence

from aegis_trade.domain.core import MarketBar
from aegis_trade.domain.features import FeatureSet, FeatureMetadata

class IFeatureExtractor(abc.ABC):
    """
    Port for extracting quantitative features from market bars.
    Implementations must return standard FeatureSet objects and not leak their 
    underlying DataFrame/ndarray representations into the domain.
    """

    @abc.abstractmethod
    def extract(self, bars: Sequence[MarketBar]) -> List[FeatureSet]:
        """
        Extracts features from the given market bars.

        Args:
            bars: A sequence of chronologically ordered MarketBar objects.

        Returns:
            A list of FeatureSet objects matching the timeframe and symbols of the bars.
        """
        pass

    @abc.abstractmethod
    def get_metadata(self) -> List[FeatureMetadata]:
        """
        Returns metadata describing the features extracted by this implementation.
        """
        pass
