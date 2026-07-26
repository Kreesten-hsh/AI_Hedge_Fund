import pandas as pd
from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping

from aegis_trade.domain.core import MarketBar, Symbol, TimeFrame

class OpenBBMapper:
    """
    Maps OpenBB raw DTOs (e.g., pandas Series/DataFrame rows) to Aegis Quant OS Domain Objects.
    """

    @staticmethod
    def map_to_market_bar(
        symbol: Symbol, 
        timeframe: TimeFrame, 
        index: object, 
        row: Mapping[str, object]
    ) -> MarketBar:
        """
        Maps a row of OHLCV data from OpenBB to a MarketBar.
        """
        if isinstance(index, pd.Timestamp) or isinstance(index, datetime):
            dt = index
        else:
            dt = pd.to_datetime(row.get("date") or index)
            
        # Ensure timezone awareness (UTC)
        if hasattr(dt, "tzinfo") and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elif hasattr(dt, "tzinfo"):
             dt = dt.astimezone(timezone.utc)
             
        if not hasattr(dt, "tzinfo"):
            dt = dt.to_pydatetime().replace(tzinfo=timezone.utc)
        
        # safely extract Decimal values
        def _get_decimal(key: str, default: Decimal = Decimal('0')) -> Decimal:
            val = row.get(key)
            if val is None or pd.isna(val):
                return default
            return Decimal(str(val))

        open_p = _get_decimal('open')
        high_p = _get_decimal('high')
        low_p = _get_decimal('low')
        close_p = _get_decimal('close')
        vol = _get_decimal('volume')

        # In some cases, we might miss some fields
        if open_p == 0 and close_p > 0:
            open_p = close_p
        if high_p == 0 and close_p > 0:
            high_p = close_p
        if low_p == 0 and close_p > 0:
            low_p = close_p

        return MarketBar(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=dt,
            open=open_p,
            high=high_p,
            low=low_p,
            close=close_p,
            volume=vol
        )
