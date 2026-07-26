from typing import Protocol, Sequence, runtime_checkable

import json
from pathlib import Path
from datetime import datetime

from aegis_trade.core.storage import StorageEngine, StorageConfig
from aegis_trade.infrastructure.storage import LocalFileSystemStorage
from aegis_trade.infrastructure.serializers import ArrowSerializer, MetadataSerializer

from aegis_trade.domain import MarketBar, Symbol, TimeFrame, AssetClass
from aegis_trade.dataset.domain import Dataset, DatasetMetadata

@runtime_checkable
class DatasetRepository(Protocol):
    def save(self, dataset: Dataset, metadata: DatasetMetadata, data: Sequence[MarketBar]) -> None:
        ...
        
    def find_datasets(self) -> Sequence[Dataset]:
        ...
        
    def load_dataset_data(self, dataset_hash: str) -> Sequence[MarketBar]:
        ...

class StorageDatasetRepository:
    def __init__(self, storage: StorageEngine | str | Path):
        if isinstance(storage, (str, Path)):
            self._storage = LocalFileSystemStorage(StorageConfig(base_path=Path(storage)))
        else:
            self._storage = storage
        self._arrow = ArrowSerializer()
        self._meta = MetadataSerializer()
        
    def _get_path(self, dataset_hash: str, filename: str) -> str:
        return f"{dataset_hash}/{filename}"

    def save(self, dataset: Dataset, metadata: DatasetMetadata, data: Sequence[MarketBar]) -> None:
        parquet_path = self._get_path(dataset.dataset_hash, "data.parquet")
        manifest_path = self._get_path(dataset.dataset_hash, "manifest.json")
        
        if self._storage.exists(parquet_path):
            return
            
        ds_info = {
            "dataset_hash": dataset.dataset_hash,
            "symbol": {"name": dataset.symbol.name, "asset_class": dataset.symbol.asset_class.value},
            "timeframe": dataset.timeframe.value if dataset.timeframe else None,
            "row_count": dataset.row_count,
            "date_start": dataset.date_start.isoformat(),
            "date_end": dataset.date_end.isoformat(),
        }
        
        meta_info = {
            "provider": metadata.provider,
            "provider_version": metadata.provider_version,
            "validator_version": metadata.validator_version,
            "builder_version": metadata.builder_version,
            "schema_version": metadata.schema_version,
        }
        
        manifest_data = self._meta.serialize({"dataset": ds_info, "metadata": meta_info})
        self._storage.save(manifest_path, manifest_data)
            
        timestamps = [b.timestamp.replace(tzinfo=None) for b in data]
        opens = [float(b.open) for b in data]
        highs = [float(b.high) for b in data]
        lows = [float(b.low) for b in data]
        closes = [float(b.close) for b in data]
        volumes = [float(b.volume) for b in data]
        
        # We pass metadata directly to ArrowSerializer
        custom_metadata = {
            b"aegis_dataset": json.dumps(ds_info).encode('utf-8'),
            b"aegis_metadata": json.dumps(meta_info).encode('utf-8')
        }
        
        table_bytes = self._arrow.serialize({
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes
        }, metadata=custom_metadata)
        
        self._storage.save(parquet_path, table_bytes)

    def find_datasets(self) -> Sequence[Dataset]:
        datasets = []
        # Pragmatic implementation for tests
        if hasattr(self._storage, 'config') and hasattr(self._storage.config, 'base_path'):
            base_path = Path(self._storage.config.base_path)
            if base_path.exists():
                for p in base_path.iterdir():
                    if p.is_dir():
                        parquet_path = p / "data.parquet"
                        manifest_path = p / "manifest.json"
                        if parquet_path.exists() and manifest_path.exists():
                            manifest_data = self._storage.load(f"{p.name}/manifest.json")
                            ds_info = self._meta.deserialize(manifest_data)["dataset"]
                            
                            dataset = Dataset(
                                dataset_hash=ds_info["dataset_hash"],
                                symbol=Symbol(name=ds_info["symbol"]["name"], asset_class=AssetClass(ds_info["symbol"]["asset_class"])),
                                timeframe=TimeFrame(ds_info["timeframe"]) if ds_info["timeframe"] else None,
                                row_count=ds_info["row_count"],
                                date_start=datetime.fromisoformat(ds_info["date_start"]),
                                date_end=datetime.fromisoformat(ds_info["date_end"])
                            )
                            datasets.append(dataset)
        return datasets

    def load_dataset_data(self, dataset_hash: str) -> Sequence[MarketBar]:
        from decimal import Decimal
        from datetime import timezone
        
        parquet_path = self._get_path(dataset_hash, "data.parquet")
        manifest_path = self._get_path(dataset_hash, "manifest.json")
        
        if not self._storage.exists(parquet_path):
            raise FileNotFoundError(f"Dataset {dataset_hash} not found in repository.")
            
        manifest_data = self._meta.deserialize(self._storage.load(manifest_path))
        ds_info = manifest_data["dataset"]
        
        symbol = Symbol(name=ds_info["symbol"]["name"], asset_class=AssetClass(ds_info["symbol"]["asset_class"]))
        timeframe = TimeFrame(ds_info["timeframe"]) if ds_info["timeframe"] else None
        
        table_bytes = self._storage.load(parquet_path)
        columns, custom_metadata = self._arrow.deserialize(table_bytes)
        
        bars = []
        for i in range(len(columns["timestamp"])):
            ts = columns["timestamp"][i]
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
                
            bars.append(MarketBar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts,
                open=Decimal(str(columns["open"][i])),
                high=Decimal(str(columns["high"][i])),
                low=Decimal(str(columns["low"][i])),
                close=Decimal(str(columns["close"][i])),
                volume=Decimal(str(columns["volume"][i]))
            ))
            
        return bars

# Alias for backward compatibility
ParquetDatasetRepository = StorageDatasetRepository
