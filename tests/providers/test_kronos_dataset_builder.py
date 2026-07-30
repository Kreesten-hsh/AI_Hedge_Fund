import pytest
import pandas as pd
import numpy as np
from aegis_trade.providers.kronos.dataset_builder import KronosDatasetBuilder

def test_build_from_dataframe_windows():
    # Setup dummy dataframe
    # We need at least 2048 + stride rows to see multiple windows
    context_length = 2048
    stride = context_length // 2
    total_rows = context_length + stride + 10
    
    df = pd.DataFrame({
        "close": np.random.rand(total_rows)
    })
    
    builder = KronosDatasetBuilder(context_length=context_length)
    
    try:
        import torch
        windows = builder.build_from_dataframe(df)
        
        assert len(windows) == 2 # (0 to 2048), (1024 to 3072)
        assert len(windows[0]) == context_length
        assert len(windows[1]) == context_length
        assert isinstance(windows[0], torch.Tensor)
    except ImportError:
        pass # Skip if torch not installed

def test_prepare_datasets_split():
    context_length = 2048
    stride = context_length // 2
    total_rows = context_length * 5 # Enough for several windows
    
    df1 = pd.DataFrame({"close": np.random.rand(total_rows)})
    df2 = pd.DataFrame({"close": np.random.rand(total_rows)})
    
    builder = KronosDatasetBuilder(context_length=context_length)
    
    try:
        import torch
        train, val = builder.prepare_datasets({"Boom_1000": df1, "Crash_1000": df2})
        
        # Each df produces some windows. Total = 2 * windows_per_df
        # 80/20 split
        assert len(train) > 0
        assert len(val) > 0
        assert len(train) >= len(val) * 3
    except ImportError:
        pass
