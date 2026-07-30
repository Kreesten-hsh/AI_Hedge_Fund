import logging
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset
from typing import List, Dict, Tuple, Any

logger = logging.getLogger(__name__)

class KronosDataset(Dataset):
    def __init__(self, windows_x: List[np.ndarray], windows_stamp: List[np.ndarray], lookback: int, clip: float = 5.0):
        self.windows_x = windows_x
        self.windows_stamp = windows_stamp
        self.lookback = lookback
        self.clip = clip

    def __len__(self):
        return len(self.windows_x)

    def __getitem__(self, idx):
        x = self.windows_x[idx]
        x_stamp = self.windows_stamp[idx]

        # Normalize based on lookback window
        past_x = x[:self.lookback]
        x_mean = np.mean(past_x, axis=0)
        x_std = np.std(past_x, axis=0)

        x = (x - x_mean) / (x_std + 1e-5)
        x = np.clip(x, -self.clip, self.clip)

        return torch.from_numpy(x).float(), torch.from_numpy(x_stamp).float()


class KronosDatasetBuilder:
    """
    Builds the dataset for fine-tuning Kronos-mini.
    Extracts sliding windows from raw OHLCV data.
    """
    def __init__(self, lookback_window: int = 90, predict_window: int = 10):
        self.lookback_window = lookback_window
        self.predict_window = predict_window
        self.window_size = lookback_window + predict_window + 1
        self.feature_list = ['open', 'high', 'low', 'close', 'volume', 'amount']
        self.time_feature_list = ['minute', 'hour', 'weekday', 'day', 'month']

    def _calc_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if 'datetime' in df.columns:
            dt = df['datetime'].dt
        else:
            dt = df.index
            
        df['minute'] = dt.minute
        df['hour'] = dt.hour
        df['weekday'] = dt.weekday
        df['day'] = dt.day
        df['month'] = dt.month
        return df

    def build_from_dataframe(self, df: pd.DataFrame) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        windows_x = []
        windows_stamp = []
        
        if df.empty:
            return windows_x, windows_stamp
            
        # Ensure all columns exist
        for col in self.feature_list:
            if col not in df.columns:
                if col == 'amount' and 'volume' in df.columns:
                    df['amount'] = df['volume'] * df[['open', 'high', 'low', 'close']].mean(axis=1)
                else:
                    df[col] = 0.0

        df = self._calc_time_features(df)
        
        x_values = df[self.feature_list].values.astype(np.float32)
        stamp_values = df[self.time_feature_list].values.astype(np.float32)
        
        stride = 10 # small stride for data augmentation
        for i in range(0, len(x_values) - self.window_size + 1, stride):
            windows_x.append(x_values[i:i + self.window_size])
            windows_stamp.append(stamp_values[i:i + self.window_size])
            
        return windows_x, windows_stamp

    def prepare_datasets(self, data_sources: Dict[str, pd.DataFrame]) -> Tuple[Dataset, Dataset]:
        """
        Prepares train and validation PyTorch datasets from a dict of symbol -> dataframe.
        """
        all_x_train, all_stamp_train = [], []
        all_x_val, all_stamp_val = [], []
        
        for symbol, df in data_sources.items():
            logger.info(f"Building dataset for {symbol} (Total rows: {len(df)})")
            wx, ws = self.build_from_dataframe(df)
            
            # Simple 80/20 split
            split_idx = int(len(wx) * 0.8)
            all_x_train.extend(wx[:split_idx])
            all_stamp_train.extend(ws[:split_idx])
            
            all_x_val.extend(wx[split_idx:])
            all_stamp_val.extend(ws[split_idx:])
            
        train_dataset = KronosDataset(all_x_train, all_stamp_train, self.lookback_window)
        val_dataset = KronosDataset(all_x_val, all_stamp_val, self.lookback_window)
            
        return train_dataset, val_dataset
