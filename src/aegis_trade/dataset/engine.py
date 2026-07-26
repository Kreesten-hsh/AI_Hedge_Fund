from typing import Sequence
from aegis_trade.domain import MarketBar
from aegis_trade.dataset.domain import Dataset
from aegis_trade.dataset.builder import DatasetBuilder
from aegis_trade.dataset.repository import DatasetRepository

class DatasetEngine:
    """Public facade for Dataset Engine operations."""
    
    def __init__(self, repository: DatasetRepository, builder: DatasetBuilder | None = None):
        self.repository = repository
        self.builder = builder or DatasetBuilder()

    def ingest_market_bars(
        self, 
        bars: Sequence[MarketBar], 
        provider: str, 
        provider_version: str = "1.0"
    ) -> Dataset[MarketBar]:
        """
        Ingests a sequence of market bars, computes the hash, creates metadata, 
        and saves everything to the repository. Returns the domain Dataset entity.
        """
        dataset, metadata = self.builder.build_market_bars(
            bars=bars, 
            provider=provider, 
            provider_version=provider_version
        )
        
        self.repository.save(dataset, metadata, bars)
        return dataset
        
    def find_datasets(self) -> Sequence[Dataset]:
        """Returns all datasets managed by the repository."""
        return self.repository.find_datasets()
        
    def load_dataset_data(self, dataset_hash: str) -> Sequence[MarketBar]:
        """Loads raw MarketBars for a specific dataset."""
        return self.repository.load_dataset_data(dataset_hash)
