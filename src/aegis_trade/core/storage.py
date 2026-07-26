from typing import Protocol, Any, Sequence, Mapping
from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class StorageConfig:
    base_path: Path
    # Additional configuration like s3 buckets, connection strings, etc. could go here

class StorageEngine(Protocol):
    """
    Hexagonal Port for raw physical storage operations.
    Handles I/O without knowing about Domain entities.
    """
    
    def save(self, path: str, data: bytes | str, **kwargs: Any) -> None:
        """Save raw bytes or string to a specific physical path."""
        ...
        
    def load(self, path: str, **kwargs: Any) -> Any:
        """Load raw data from a specific physical path."""
        ...
        
    def delete(self, path: str) -> None:
        """Delete data at a specific physical path."""
        ...
        
    def exists(self, path: str) -> bool:
        """Check if data exists at a specific physical path."""
        ...


class Serializer(Protocol):
    """
    Hexagonal Port for Serialization.
    Transforms Domain Entities / Data Structures to bytes or primitives, and vice versa.
    """
    def serialize(self, obj: Any) -> Any:
        ...
        
    def deserialize(self, data: Any) -> Any:
        ...
