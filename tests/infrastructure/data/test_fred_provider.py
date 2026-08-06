from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from aegis_trade.domain.core import AssetClass, Symbol
from aegis_trade.domain.exceptions.data import DataProviderError
from aegis_trade.infrastructure.data.providers.fred_provider import FredDataProvider


def test_fred_provider_no_key_warning():
    provider = FredDataProvider(api_key=None)
    assert provider._fred is None
    symbol = Symbol(name="DFII10", asset_class=AssetClass.INDICES)
    with pytest.raises(DataProviderError, match="FRED API key non configurée"):
        provider.fetch_series("DFII10")


@patch("aegis_trade.infrastructure.data.providers.fred_provider.Fred")
def test_fred_provider_fetch_series_success(mock_fred_cls):
    mock_fred_inst = MagicMock()
    mock_fred_cls.return_value = mock_fred_inst
    
    # Mocking pandas Series return from Fred.get_series
    mock_series = pd.Series(
        [1.85, 1.90],
        index=pd.to_datetime(["2026-08-01", "2026-08-02"])
    )
    mock_fred_inst.get_series.return_value = mock_series

    provider = FredDataProvider(api_key="test_api_key")
    series = provider.fetch_series("DFII10", start_date=datetime(2026, 8, 1), end_date=datetime(2026, 8, 2))

    assert len(series) == 2
    assert series.iloc[0] == 1.85
    mock_fred_inst.get_series.assert_called_once_with(
        "DFII10",
        observation_start="2026-08-01",
        observation_end="2026-08-02",
    )


@patch("aegis_trade.infrastructure.data.providers.fred_provider.Fred")
def test_fred_provider_fetch_macro(mock_fred_cls):
    mock_fred_inst = MagicMock()
    mock_fred_cls.return_value = mock_fred_inst

    mock_series = pd.Series(
        [1.85],
        index=pd.to_datetime(["2026-08-01"])
    )
    mock_fred_inst.get_series.return_value = mock_series

    provider = FredDataProvider(api_key="test_api_key")
    symbol = Symbol(name="DFII10", asset_class=AssetClass.INDICES)
    indicators = provider.fetch_macro(
        symbol,
        start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        end=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )

    assert len(indicators) == 1
    assert indicators[0].symbol.name == "DFII10"
    assert str(indicators[0].value) == "1.85"
