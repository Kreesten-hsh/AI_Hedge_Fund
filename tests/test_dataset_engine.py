import unittest
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.domain import MarketBar, Symbol, AssetClass, TimeFrame
from aegis_trade.dataset.engine import DatasetEngine
from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.infrastructure.storage import ParquetStorageEngine
from aegis_trade.core.storage import StorageConfig

class TestDatasetEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = Path(self.temp_dir) / "datasets"
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_dataset_engine_ingest_and_load(self):
        config = StorageConfig(base_path=self.storage_dir)
        repository = StorageDatasetRepository(storage=ParquetStorageEngine(config))
        engine = DatasetEngine(repository=repository)
        
        symbol = Symbol(name="BTCUSD", asset_class=AssetClass.CRYPTO)
        
        bars = [
            MarketBar(
                symbol=symbol,
                timeframe=TimeFrame.M5,
                timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
                open=Decimal("40000.0"),
                high=Decimal("40100.0"),
                low=Decimal("39900.0"),
                close=Decimal("40050.0"),
                volume=Decimal("2.5")
            ),
            MarketBar(
                symbol=symbol,
                timeframe=TimeFrame.M5,
                timestamp=datetime(2024, 1, 1, 10, 5, tzinfo=timezone.utc),
                open=Decimal("40050.0"),
                high=Decimal("40200.0"),
                low=Decimal("40000.0"),
                close=Decimal("40150.0"),
                volume=Decimal("3.0")
            )
        ]
        
        dataset = engine.ingest_market_bars(bars, provider="test_provider")
        
        self.assertEqual(dataset.symbol, symbol)
        self.assertEqual(dataset.timeframe, TimeFrame.M5)
        self.assertEqual(dataset.row_count, 2)
        self.assertEqual(dataset.date_start, bars[0].timestamp)
        self.assertEqual(dataset.date_end, bars[1].timestamp)
        self.assertIsNotNone(dataset.dataset_hash)
        
        datasets = engine.find_datasets()
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].dataset_hash, dataset.dataset_hash)
        
        loaded_bars = engine.load_dataset_data(dataset.dataset_hash)
        self.assertEqual(len(loaded_bars), 2)
        self.assertEqual(loaded_bars[0].timestamp, bars[0].timestamp)
        self.assertEqual(loaded_bars[0].close, bars[0].close)

    def test_repository_idempotence(self):
        config = StorageConfig(base_path=self.storage_dir)
        repository = StorageDatasetRepository(storage=ParquetStorageEngine(config))
        engine = DatasetEngine(repository=repository)
        
        symbol = Symbol(name="ETHUSD", asset_class=AssetClass.CRYPTO)
        
        bar = MarketBar(
            symbol=symbol,
            timeframe=TimeFrame.H1,
            timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            open=Decimal("2000.0"),
            high=Decimal("2010.0"),
            low=Decimal("1990.0"),
            close=Decimal("2005.0"),
            volume=Decimal("10.0")
        )
        
        dataset1 = engine.ingest_market_bars([bar], provider="test_provider")
        
        # Manually alter the manifest or parquet to see if it gets overwritten
        ds_dir = self.storage_dir / dataset1.dataset_hash
        manifest_path = ds_dir / "manifest.json"
        
        # Read and modify manifest
        with open(manifest_path, "a") as f:
            f.write("\n")
        
        mtime_before = manifest_path.stat().st_mtime
        
        # Re-ingest
        dataset2 = engine.ingest_market_bars([bar], provider="test_provider")
        
        mtime_after = manifest_path.stat().st_mtime
        
        # Mtime should be exactly the same, as it should be skipped
        self.assertEqual(mtime_before, mtime_after)
        self.assertEqual(dataset1.dataset_hash, dataset2.dataset_hash)
