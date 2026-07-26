import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.exceptions.data import DataProviderError
from aegis_trade.infrastructure.data.providers.openbb_provider import OpenBBDataProvider

@patch("aegis_trade.infrastructure.data.providers.openbb_provider.obb")
def test_openbb_empty_dataframe(mock_obb):
    mock_res = MagicMock()
    mock_res.to_df.return_value = pd.DataFrame()
    mock_obb.index.price.historical.return_value = mock_res
    
    provider = OpenBBDataProvider()
    sym = Symbol("DXY", AssetClass.INDICES)
    
    bars = provider.fetch_ohlcv(sym, TimeFrame.D1, datetime(2023, 1, 1), datetime(2023, 1, 2))
    assert bars == []

@patch("aegis_trade.infrastructure.data.providers.openbb_provider.obb")
def test_openbb_network_error_raises_data_provider_error(mock_obb):
    # Simulate a network error (e.g. timeout)
    mock_obb.index.price.historical.side_effect = Exception("Connection Timeout")
    
    provider = OpenBBDataProvider()
    # reduce retries for fast testing, we can mock tenacity's wait logic if needed, 
    # but here we'll just let it fail after attempts
    sym = Symbol("DXY", AssetClass.INDICES)
    
    with pytest.raises(DataProviderError, match="OpenBB API Error: Connection Timeout"):
        provider.fetch_ohlcv(sym, TimeFrame.D1, datetime(2023, 1, 1), datetime(2023, 1, 2))
