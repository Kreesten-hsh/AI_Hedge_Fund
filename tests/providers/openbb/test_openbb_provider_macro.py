from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from aegis_trade.domain.core import AssetClass, Symbol
from aegis_trade.domain.exceptions.data import DataProviderError
from aegis_trade.infrastructure.data.providers.openbb_provider import OpenBBDataProvider


@patch("aegis_trade.infrastructure.data.providers.openbb_provider.obb")
def test_openbb_fetch_macro_fred_success(mock_obb):
    mock_res = MagicMock()
    mock_df = pd.DataFrame(
        {"value": [1.85, 1.90]},
        index=pd.to_datetime(["2026-08-01", "2026-08-02"])
    )
    mock_res.to_df.return_value = mock_df
    mock_obb.economy.fred_series.return_value = mock_res

    provider = OpenBBDataProvider()
    symbol = Symbol(name="DFII10", asset_class=AssetClass.INDICES)
    indicators = provider.fetch_macro(
        symbol,
        start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        end=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )

    assert len(indicators) == 2
    assert indicators[0].symbol.name == "DFII10"
    assert str(indicators[0].value) == "1.85"
    mock_obb.economy.fred_series.assert_called_once_with(
        symbol="DFII10",
        provider="fred",
        start_date="2026-08-01",
        end_date="2026-08-02",
        timeout=15,
    )


@patch("aegis_trade.infrastructure.data.providers.openbb_provider.obb")
def test_openbb_fetch_macro_fred_error(mock_obb):
    mock_obb.economy.fred_series.side_effect = Exception("FRED provider error")

    provider = OpenBBDataProvider()
    symbol = Symbol(name="DFII10", asset_class=AssetClass.INDICES)

    with pytest.raises(DataProviderError, match="OpenBB FRED API Error"):
        provider.fetch_macro(
            symbol,
            start=datetime(2026, 8, 1, tzinfo=timezone.utc),
            end=datetime(2026, 8, 2, tzinfo=timezone.utc),
        )
