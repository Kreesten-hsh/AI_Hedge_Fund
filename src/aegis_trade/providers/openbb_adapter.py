import pandas as pd
from datetime import datetime, timezone
from openbb import obb

from aegis_trade.domain import MarketBar, Symbol, AssetClass, TimeFrame

class OpenBBAdapter:
    """
    Adapter for OpenBB SDK (v4) to extract macro and fundamental data
    and convert it to Aegis Quant OS domain entities (MarketBar).
    """

    def __init__(self):
        # OpenBB initialization is usually automatic upon import
        pass

    def fetch_dxy(self, start_date: str, end_date: str) -> list[MarketBar]:
        """
        Fetches the US Dollar Index (DXY) using OpenBB and maps it to MarketBars.
        Uses yfinance as provider for DX-Y.NYB.
        """
        # Fetch data
        res = obb.equity.price.historical(
            symbol="DX-Y.NYB",
            provider="yfinance",
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )
        df = res.to_df()
        
        # In openbb v4 with yfinance, the index is usually the date
        symbol = Symbol(name="DXY", asset_class=AssetClass.INDICES)
        bars = []
        
        for dt, row in df.iterrows():
            import datetime as dt_mod
            if isinstance(dt, str):
                dt_obj = datetime.fromisoformat(dt)
            elif isinstance(dt, dt_mod.datetime):
                dt_obj = dt
            elif isinstance(dt, dt_mod.date):
                dt_obj = datetime.combine(dt, dt_mod.time.min)
            else:
                try:
                    dt_obj = dt.to_pydatetime()
                except Exception:
                    dt_obj = pd.to_datetime(dt).to_pydatetime()
            
            # Ensure timezone awareness
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(tzinfo=timezone.utc)
            else:
                dt_obj = dt_obj.astimezone(timezone.utc)
                
            close_p = float(row["close"])
            if pd.isna(close_p) or close_p <= 0:
                continue

            open_p = float(row.get("open", row.get("close", 0)))
            high_p = float(row.get("high", row.get("close", 0)))
            low_p = float(row.get("low", row.get("close", 0)))
            vol = float(row.get("volume", 0))
            
            bars.append(MarketBar(
                symbol=symbol,
                timeframe=TimeFrame.D1,
                timestamp=dt_obj,
                open=open_p,
                high=high_p,
                low=low_p,
                close=close_p,
                volume=vol
            ))
            
        return bars

    def fetch_us10y(self, start_date: str, end_date: str) -> list[MarketBar]:
        """
        Fetches US 10-Year Treasury yield (^TNX) via OpenBB using yfinance
        to avoid FRED API key requirement.
        Maps the daily OHLC values to MarketBars.
        """
        res = obb.equity.price.historical(
            symbol="^TNX",
            provider="yfinance",
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )
        df = res.to_df()
        
        symbol = Symbol(name="US10Y", asset_class=AssetClass.INDICES)
        bars = []
        
        for dt, row in df.iterrows():
            import datetime as dt_mod
            if isinstance(dt, str):
                dt_obj = datetime.fromisoformat(dt)
            elif isinstance(dt, dt_mod.datetime):
                dt_obj = dt
            elif isinstance(dt, dt_mod.date):
                dt_obj = datetime.combine(dt, dt_mod.time.min)
            else:
                try:
                    dt_obj = dt.to_pydatetime()
                except Exception:
                    dt_obj = pd.to_datetime(dt).to_pydatetime()
            
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(tzinfo=timezone.utc)
            else:
                dt_obj = dt_obj.astimezone(timezone.utc)
            
            close_p = float(row["close"])
            if pd.isna(close_p) or close_p <= 0:
                continue
                
            open_p = float(row.get("open", close_p))
            high_p = float(row.get("high", close_p))
            low_p = float(row.get("low", close_p))
            
            bars.append(MarketBar(
                symbol=symbol,
                timeframe=TimeFrame.D1,
                timestamp=dt_obj,
                open=open_p,
                high=high_p,
                low=low_p,
                close=close_p,
                volume=0.0
            ))
            
        return bars
