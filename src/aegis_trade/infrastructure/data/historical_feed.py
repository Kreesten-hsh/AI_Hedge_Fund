from typing import Iterator

from aegis_trade.domain.core import Symbol, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.infrastructure.features.feature_store import FeatureStore

class FeatureStoreFeed(IDataFeed):
    """
    Adapter that implements IDataFeed by reading sequentially from the FeatureStore.
    """
    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store

    def get_feature_stream(self, symbol: Symbol, timeframe: TimeFrame) -> Iterator[FeatureSet]:
        """
        Loads all features for a symbol and timeframe into memory and yields them one by one.
        Suitable for simulation / backtesting where sequential time flow is required.
        """
        # Load all features (they come sorted chronologically from FeatureStore)
        feature_sets = self.feature_store.load_features(symbol, timeframe)
        
        for fs in feature_sets:
            yield fs
