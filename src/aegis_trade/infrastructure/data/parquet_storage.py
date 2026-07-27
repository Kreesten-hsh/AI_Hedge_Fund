import os
import pandas as pd
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from aegis_trade.domain.core import MarketBar, Symbol, TimeFrame
from aegis_trade.domain.exceptions.data import StorageError

class ParquetStorage:
    """
    Local Data Lake using Parquet.
    Implements Delta synchronization logic (upsert) to persist MarketBars and minimize network queries.
    """
    def __init__(self, data_dir: str = "data/market_data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_file_path(self, symbol: Symbol, timeframe: TimeFrame) -> str:
        return os.path.join(self.data_dir, f"{symbol.name}_{timeframe.value}.parquet")

    def load_bars(self, symbol: Symbol, timeframe: TimeFrame) -> Sequence[MarketBar]:
        file_path = self._get_file_path(symbol, timeframe)
        if not os.path.exists(file_path):
            return []
            
        try:
            df = pd.read_parquet(file_path)
            if df.empty:
                return []
                
            bars = []
            from datetime import timezone
            for _, row in df.iterrows():
                # Assure that timestamp is a python datetime with UTC tzinfo
                ts = pd.Timestamp(row['timestamp']).to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                else:
                    ts = ts.astimezone(timezone.utc)
                    
                bar = MarketBar(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=ts,
                    open=Decimal(str(row['open'])),
                    high=Decimal(str(row['high'])),
                    low=Decimal(str(row['low'])),
                    close=Decimal(str(row['close'])),
                    volume=Decimal(str(row['volume']))
                )
                bars.append(bar)
            return bars
        except Exception as e:
            raise StorageError(f"Failed to load Parquet file {file_path}: {e}") from e

    def save_and_merge_bars(self, symbol: Symbol, timeframe: TimeFrame, new_bars: Sequence[MarketBar]) -> Sequence[MarketBar]:
        if not new_bars:
            return self.load_bars(symbol, timeframe)
            
        file_path = self._get_file_path(symbol, timeframe)
        
        try:
            new_df = pd.DataFrame([{
                'timestamp': b.timestamp,
                'open': float(b.open),
                'high': float(b.high),
                'low': float(b.low),
                'close': float(b.close),
                'volume': float(b.volume)
            } for b in new_bars])
            
            if os.path.exists(file_path):
                existing_df = pd.read_parquet(file_path)
                combined_df = pd.concat([existing_df, new_df])
            else:
                combined_df = new_df
                
            # Deduplicate by timestamp and sort
            combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
            
            # Save
            combined_df.to_parquet(file_path, index=False)
            
            # Convert back to domain objects to return the full unified history
            bars = []
            from datetime import timezone
            for _, row in combined_df.iterrows():
                ts = pd.Timestamp(row['timestamp']).to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                else:
                    ts = ts.astimezone(timezone.utc)
                    
                bar = MarketBar(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=ts,
                    open=Decimal(str(row['open'])),
                    high=Decimal(str(row['high'])),
                    low=Decimal(str(row['low'])),
                    close=Decimal(str(row['close'])),
                    volume=Decimal(str(row['volume']))
                )
                bars.append(bar)
            return bars
            
        except Exception as e:
            raise StorageError(f"Failed to save/merge Parquet file {file_path}: {e}") from e

    def get_latest_timestamp(self, symbol: Symbol, timeframe: TimeFrame) -> datetime | None:
        file_path = self._get_file_path(symbol, timeframe)
        if not os.path.exists(file_path):
            return None
            
        try:
            df = pd.read_parquet(file_path, columns=['timestamp'])
            if df.empty:
                return None
            from datetime import timezone
            ts = df['timestamp'].max()
            if pd.isna(ts):
                return None
            ts = pd.Timestamp(ts).to_pydatetime()
            if ts.tzinfo is None:
                return ts.replace(tzinfo=timezone.utc)
            return ts.astimezone(timezone.utc)
        except Exception as e:
            raise StorageError(f"Failed to read latest timestamp from {file_path}: {e}") from e
