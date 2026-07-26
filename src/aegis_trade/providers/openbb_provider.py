import logging
from datetime import datetime
from typing import Sequence
import pandas as pd
from openbb import obb

from aegis_trade.domain import MarketBar, Symbol, TimeFrame

logger = logging.getLogger(__name__)

class OpenBBProvider:
    """
    Data provider using OpenBB (v4) for macroeconomic data and alternative datasets.
    """

    def __init__(self):
        # We can configure api keys here later if needed
        self.provider = "yfinance"

    def fetch_historical_data(self, symbol: Symbol, timeframe: TimeFrame, start: datetime, end: datetime) -> Sequence[MarketBar]:
        """
        Fetch historical data and convert to MarketBar domain objects.
        """
        logger.info(f"Fetching OpenBB data for {symbol.name} ({timeframe}) from {start} to {end}")
        
        # Mappings for macro symbols to yfinance equivalents if we use yfinance provider
        # DXY = DX-Y.NYB, US10Y = ^TNX
        ticker_map = {
            "DXY": "DX-Y.NYB",
            "US10Y": "^TNX"
        }
        
        target_ticker = ticker_map.get(symbol.name, symbol.name)
        
        # We need to map Aegis TimeFrame to OpenBB interval
        # openbb equity.price.historical supports intervals like '1d', '1h', etc.
        interval_map = {
            TimeFrame.M1: "1m",
            TimeFrame.M5: "5m",
            TimeFrame.M15: "15m",
            TimeFrame.H1: "1h",
            TimeFrame.H4: "1d", # openbb yfinance might not support 4h well, but let's assume it works or fallback to 1d
            TimeFrame.D1: "1d"
        }
        
        interval = interval_map.get(timeframe, "1d")
        
        try:
            # Note: in openbb v4, the signature often uses start_date and end_date as strings or dates
            res = obb.equity.price.historical(
                symbol=target_ticker,
                provider=self.provider,
                interval=interval,
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d")
            )
            df = res.to_df()
            # Convert columns to lowercase for consistency
            df.columns = [c.lower() for c in df.columns]
        except Exception as e:
            logger.error(f"Failed to fetch data from OpenBB for {symbol.name}: {e}")
            return []

        if df.empty:
            logger.warning(f"No data returned for {symbol.name}")
            return []
            
        # The DataFrame typically has the date as index or 'date' column
        # columns: open, high, low, close, volume
        bars = []
        for index, row in df.iterrows():
            # If the index is a datetime, use it. Otherwise, look for 'date' column
            if isinstance(index, pd.Timestamp) or isinstance(index, datetime):
                dt = index
            else:
                dt = pd.to_datetime(row.get("date") or index)
                
            # Ensure timezone awareness
            if dt.tzinfo is None:
                dt = dt.tz_localize('UTC')
            
            from decimal import Decimal
            try:
                bar = MarketBar(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=dt,
                    open=Decimal(str(row['open'])),
                    high=Decimal(str(row['high'])),
                    low=Decimal(str(row['low'])),
                    close=Decimal(str(row['close'])),
                    volume=Decimal(str(row.get('volume', 0)))
                )
                bars.append(bar)
            except KeyError as e:
                logger.error(f"Missing column in OpenBB data: {e}")
                continue

        logger.info(f"Fetched {len(bars)} bars for {symbol.name}")
        return bars
