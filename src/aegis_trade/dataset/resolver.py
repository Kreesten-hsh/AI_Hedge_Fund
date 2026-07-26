from typing import Optional, Sequence

from aegis_trade.domain import Symbol, TimeFrame, MarketBar
from aegis_trade.dataset.domain import Dataset
from aegis_trade.dataset.repository import DatasetRepository

class DatasetResolver:
    def __init__(self, repository: DatasetRepository):
        self.repository = repository

    def resolve_latest(self, symbol: str, timeframe: str) -> Dataset:
        """
        Resolves the most recent dataset for the given symbol and timeframe.
        Raises ValueError if no matching dataset is found.
        """
        datasets = self.repository.find_datasets()
        
        # Filter by symbol and timeframe
        matching = [
            d for d in datasets 
            if d.symbol.name == symbol and (d.timeframe and d.timeframe.value == timeframe)
        ]
        
        if not matching:
            raise ValueError(f"No dataset found for symbol {symbol} and timeframe {timeframe}")
            
        # Sort by date_end descending, then row_count descending to prefer largest dataset
        matching.sort(key=lambda d: (d.date_end, d.row_count), reverse=True)
        return matching[0]

    def load_data(self, dataset: Dataset) -> Sequence[MarketBar]:
        """
        Helper to load the actual MarketBar data for a given dataset.
        """
        return self.repository.load_dataset_data(dataset.dataset_hash)
