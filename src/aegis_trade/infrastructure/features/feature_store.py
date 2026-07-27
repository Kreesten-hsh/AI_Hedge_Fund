import os
import logging
from pathlib import Path
from typing import List, Optional
import pandas as pd
from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.domain.core import Symbol, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.exceptions.data import StorageError

logger = logging.getLogger(__name__)

class FeatureStore:
    """
    Parquet-based local storage for FeatureSets.
    Follows the same mechanics as ParquetStorage but specialized for features.
    """

    def __init__(self, data_dir: str = "data/features"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, symbol: Symbol, timeframe: TimeFrame) -> Path:
        return self.data_dir / f"{symbol.name}_{timeframe.value}_features.parquet"

    def get_latest_timestamp(self, symbol: Symbol, timeframe: TimeFrame) -> Optional[datetime]:
        """Returns the most recent UTC timestamp stored, or None if no data."""
        file_path = self._get_file_path(symbol, timeframe)
        if not file_path.exists():
            return None

        try:
            # We can use pandas to read just the timestamp column for speed
            # Since parquet supports column selection, this avoids loading the whole dataset
            df = pd.read_parquet(file_path, columns=['timestamp'])
            if df.empty:
                return None
                
            latest = df['timestamp'].max()
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            return latest.to_pydatetime()
        except Exception as e:
            logger.error(f"Failed to read latest timestamp from {file_path}: {e}")
            return None

    def save_and_merge_features(self, symbol: Symbol, timeframe: TimeFrame, new_features: List[FeatureSet]) -> None:
        """
        Saves new features and merges them with existing ones.
        Deduplicates by timestamp, keeping the new data.
        """
        if not new_features:
            return

        file_path = self._get_file_path(symbol, timeframe)
        
        # 1. Convert new features to a flat dictionary format for pandas
        records = []
        for fs in new_features:
            record = {
                "timestamp": fs.timestamp,
                **fs.features
            }
            records.append(record)
            
        new_df = pd.DataFrame(records)
        new_df['timestamp'] = pd.to_datetime(new_df['timestamp'], utc=True)

        if file_path.exists():
            try:
                old_df = pd.read_parquet(file_path)
                old_df['timestamp'] = pd.to_datetime(old_df['timestamp'], utc=True)
                
                # Concat and drop duplicates, keeping the last (newest)
                merged_df = pd.concat([old_df, new_df])
                merged_df = merged_df.drop_duplicates(subset=['timestamp'], keep='last')
                merged_df = merged_df.sort_values('timestamp').reset_index(drop=True)
            except Exception as e:
                raise StorageError(f"Failed to merge existing features in {file_path}: {e}") from e
        else:
            merged_df = new_df.sort_values('timestamp').reset_index(drop=True)

        # 2. Write back to parquet
        try:
            merged_df.to_parquet(file_path, index=False)
        except Exception as e:
            raise StorageError(f"Failed to write features to {file_path}: {e}") from e

    def load_features(self, symbol: Symbol, timeframe: TimeFrame) -> List[FeatureSet]:
        """
        Loads all stored features for a symbol and timeframe.
        """
        file_path = self._get_file_path(symbol, timeframe)
        if not file_path.exists():
            return []

        try:
            df = pd.read_parquet(file_path)
            if df.empty:
                return []
                
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
            # Reconstruct FeatureSet objects
            feature_sets = []
            
            # All columns except timestamp are considered features
            feature_cols = [c for c in df.columns if c != 'timestamp']
            
            for _, row in df.iterrows():
                # Extract features, replacing NaNs with None
                row_dict = row[feature_cols].replace({pd.NA: None, float('nan'): None}).to_dict()
                
                fs = FeatureSet(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=row['timestamp'].to_pydatetime(),
                    features=row_dict
                )
                feature_sets.append(fs)
                
            return feature_sets
        except Exception as e:
            raise StorageError(f"Failed to load features from {file_path}: {e}") from e
