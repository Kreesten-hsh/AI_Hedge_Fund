import os
from typing import Any
from pathlib import Path
from aegis_trade.core.storage import StorageEngine, StorageConfig

class LocalFileSystemStorage(StorageEngine):
    """Local file system storage implementation. Writes raw bytes or strings."""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        
    def _get_full_path(self, path: str) -> Path:
        return self.config.base_path / path

    def save(self, path: str, data: bytes | str, **kwargs: Any) -> None:
        full_path = self._get_full_path(path)
        os.makedirs(full_path.parent, exist_ok=True)
        
        mode = "wb" if isinstance(data, bytes) else "w"
        encoding = None if isinstance(data, bytes) else "utf-8"
        
        with open(full_path, mode, encoding=encoding) as f:
            f.write(data)

    def load(self, path: str, **kwargs: Any) -> bytes | str:
        full_path = self._get_full_path(path)
        # Attempt to read as string, if UnicodeDecodeError, fallback to bytes
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(full_path, "rb") as f:
                return f.read()

    def delete(self, path: str) -> None:
        full_path = self._get_full_path(path)
        if full_path.exists():
            os.remove(full_path)

    def exists(self, path: str) -> bool:
        return self._get_full_path(path).exists()

# Aliases to maintain test compatibility without duplicating classes
ParquetStorageEngine = LocalFileSystemStorage
JsonStorageEngine = LocalFileSystemStorage
