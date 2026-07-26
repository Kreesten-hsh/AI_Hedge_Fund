import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.dataset.resolver import DatasetResolver
from aegis_trade.dataset.domain import Dataset
from aegis_trade.providers.openbb_adapter import OpenBBAdapter

def main():
    repo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "datasets")
    repo = StorageDatasetRepository(repo_path)
    resolver = DatasetResolver(repo)

    print("Loading XAUUSD H1 reference dataset...")
    xau_dataset = resolver.resolve_latest("XAUUSD", "H1")
    xau_bars = resolver.load_data(xau_dataset)
    
    if not xau_bars:
        print("Error: No data in XAUUSD H1 dataset.")
        return

    start_date = xau_bars[0].timestamp.strftime("%Y-%m-%d")
    end_date = xau_bars[-1].timestamp.strftime("%Y-%m-%d")
    print(f"Time window aligned to XAUUSD: {start_date} -> {end_date}")

    adapter = OpenBBAdapter()

    from aegis_trade.domain import Symbol, AssetClass, TimeFrame
    from aegis_trade.dataset.domain import Dataset, DatasetMetadata
    import hashlib

    print("Fetching DXY via OpenBB...")
    try:
        dxy_bars = adapter.fetch_dxy(start_date=start_date, end_date=end_date)
        print(f"Fetched {len(dxy_bars)} DXY daily bars.")
        
        if dxy_bars:
            ds_dxy = Dataset(
                dataset_hash=hashlib.md5(b"DXY_D1").hexdigest(),
                symbol=Symbol("DXY", AssetClass.INDICES),
                timeframe=TimeFrame.D1,
                row_count=len(dxy_bars),
                date_start=dxy_bars[0].timestamp,
                date_end=dxy_bars[-1].timestamp
            )
            meta_dxy = DatasetMetadata(
                dataset_hash=ds_dxy.dataset_hash,
                provider="openbb", 
                provider_version="4.0", 
                validator_version="1.0", 
                builder_version="1.0", 
                schema_version="1.0"
            )
            repo.save(ds_dxy, meta_dxy, dxy_bars)
            print(f"Saved DXY dataset: {ds_dxy.dataset_hash}")
    except Exception as e:
        print(f"Failed to fetch/save DXY: {e}")

    print("Fetching US10Y via OpenBB...")
    try:
        us10y_bars = adapter.fetch_us10y(start_date=start_date, end_date=end_date)
        print(f"Fetched {len(us10y_bars)} US10Y daily bars.")
        
        if us10y_bars:
            ds_us10y = Dataset(
                dataset_hash=hashlib.md5(b"US10Y_D1").hexdigest(),
                symbol=Symbol("US10Y", AssetClass.INDICES),
                timeframe=TimeFrame.D1,
                row_count=len(us10y_bars),
                date_start=us10y_bars[0].timestamp,
                date_end=us10y_bars[-1].timestamp
            )
            meta_us10y = DatasetMetadata(
                dataset_hash=ds_us10y.dataset_hash,
                provider="openbb", 
                provider_version="4.0", 
                validator_version="1.0", 
                builder_version="1.0", 
                schema_version="1.0"
            )
            repo.save(ds_us10y, meta_us10y, us10y_bars)
            print(f"Saved US10Y dataset: {ds_us10y.dataset_hash}")
    except Exception as e:
        print(f"Failed to fetch/save US10Y: {e}")

    print("Ingestion Macro via OpenBB complete.")

if __name__ == "__main__":
    main()
