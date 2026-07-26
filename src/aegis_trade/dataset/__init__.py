"""
Aegis Quant OS - Dataset API
"""

# Public API (Domain & Value Objects)
from .domain import Dataset, DatasetMetadata

# Ports (Interfaces)
from .readonly import ReadOnlyDataset
from .repository import DatasetRepository, ParquetDatasetRepository

# Engines (Use Cases)
from .engine import DatasetEngine
from .resolver import DatasetResolver

# Internal API
from .builder import DatasetBuilder
from .hash import compute_dataset_hash

__all__ = [
    # Domain
    "Dataset",
    "DatasetMetadata",
    
    # Ports
    "ReadOnlyDataset",
    "DatasetRepository",
    "ParquetDatasetRepository",
    
    # Engines
    "DatasetEngine",
    "DatasetResolver",
    
    # Internal
    "DatasetBuilder",
    "compute_dataset_hash"
]
