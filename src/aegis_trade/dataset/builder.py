from typing import Sequence, TypeVar
from aegis_trade.domain import MarketBar
from aegis_trade.dataset.domain import Dataset, DatasetMetadata
from aegis_trade.dataset.hash import compute_dataset_hash

T = TypeVar('T')

class DatasetBuilder:
    """Stateless builder for creating Dataset and DatasetMetadata entities."""
    
    def __init__(self, builder_version: str = "1.0", validator_version: str = "1.0"):
        self.builder_version = builder_version
        self.validator_version = validator_version

    def build_market_bars(
        self, 
        bars: Sequence[MarketBar], 
        provider: str, 
        provider_version: str = "1.0"
    ) -> tuple[Dataset[MarketBar], DatasetMetadata]:
        if not bars:
            raise ValueError("Cannot build a dataset from an empty sequence of bars.")
            
        symbol = bars[0].symbol
        timeframe = bars[0].timeframe
        
        # Verify homogeneity
        for bar in bars:
            if bar.symbol != symbol or bar.timeframe != timeframe:
                raise ValueError("All bars in the dataset must have the same symbol and timeframe.")
                
        # To avoid strictly relying on pre-sorted data, we take the min/max accurately.
        date_start = min(b.timestamp for b in bars)
        date_end = max(b.timestamp for b in bars)
        row_count = len(bars)
        
        # Compute deterministic hash
        dataset_hash = compute_dataset_hash(symbol, timeframe, bars)
        
        dataset = Dataset[MarketBar](
            dataset_hash=dataset_hash,
            symbol=symbol,
            timeframe=timeframe,
            row_count=row_count,
            date_start=date_start,
            date_end=date_end
        )
        
        metadata = DatasetMetadata(
            dataset_hash=dataset_hash,
            provider=provider,
            provider_version=provider_version,
            validator_version=self.validator_version,
            builder_version=self.builder_version
        )
        
        return dataset, metadata
