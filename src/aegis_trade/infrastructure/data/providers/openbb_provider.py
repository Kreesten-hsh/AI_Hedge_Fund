import logging
from datetime import datetime
from typing import Sequence
from openbb import obb
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from aegis_trade.domain.core import (
    Symbol,
    TimeFrame,
    MarketBar,
    EconomicIndicator,
    MarketSnapshot,
    NewsItem
)
from aegis_trade.domain.ports.data_provider import IDataProvider
from aegis_trade.domain.exceptions.data import DataProviderError
from aegis_trade.infrastructure.data.mappers.openbb_mapper import OpenBBMapper

logger = logging.getLogger(__name__)

class OpenBBDataProvider(IDataProvider):
    """
    Implementation of IDataProvider using OpenBB (v4).
    Returns purely domain objects and handles API errors securely with retries.
    """

    def __init__(self, default_provider: str = "yfinance", timeout: int = 15):
        self.default_provider = default_provider
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DataProviderError),
        reraise=True
    )
    def fetch_ohlcv(
        self, symbol: Symbol, timeframe: TimeFrame, start: datetime, end: datetime
    ) -> Sequence[MarketBar]:
        
        # Mapping timeframe to OpenBB interval
        interval_map = {
            TimeFrame.M1: "1m",
            TimeFrame.M5: "5m",
            TimeFrame.M15: "15m",
            TimeFrame.M30: "30m",
            TimeFrame.H1: "1h",
            TimeFrame.H4: "1d", # yfinance limit workaround
            TimeFrame.D1: "1d"
        }
        interval = interval_map.get(timeframe, "1d")
        
        # Hardcode ticker map for known symbols
        ticker_map = {
            "DXY": "DX-Y.NYB",
            "US10Y": "^TNX",
            "DFII10": "DFII10",
            "REAL_RATE_10Y": "DFII10",
            "XAUUSD": "GC=F",
            "GOLD": "GC=F",
        }
        target_ticker = ticker_map.get(symbol.name, symbol.name)
        
        try:
            # Equity price historical for commodities/stocks, index/fred for macro indices
            if symbol.name in ["DXY", "US10Y", "DFII10", "REAL_RATE_10Y"]:
                res = obb.index.price.historical(  # type: ignore[union-attr]
                    symbol=target_ticker,
                    provider=self.default_provider,
                    interval=interval,
                    start_date=start.strftime("%Y-%m-%d"),
                    end_date=end.strftime("%Y-%m-%d"),
                    timeout=self.timeout
                )
            else:
                res = obb.equity.price.historical(  # type: ignore[union-attr]
                    symbol=target_ticker,
                    provider=self.default_provider,
                    interval=interval,
                    start_date=start.strftime("%Y-%m-%d"),
                    end_date=end.strftime("%Y-%m-%d"),
                    timeout=self.timeout
                )
            df = res.to_df()
            
            if df.empty:
                logger.warning(f"OpenBB returned empty data for {symbol.name} ({start} - {end})")
                return []
                
            df.columns = [str(c).lower() for c in df.columns]
            
        except Exception as e:
            logger.error(f"OpenBB network/API failed to fetch OHLCV for {symbol.name}: {e}")
            raise DataProviderError(f"OpenBB API Error: {e}") from e
            
        bars = []
        for index, row in df.iterrows():
            try:
                bar = OpenBBMapper.map_to_market_bar(symbol, timeframe, index, dict(row))
                bars.append(bar)
            except Exception as e:
                logger.warning(f"Failed to map row for {symbol.name} at {index}: {e}")
                
        return bars

    def fetch_macro(
        self, symbol: Symbol, start: datetime, end: datetime
    ) -> Sequence[EconomicIndicator]:
        raise NotImplementedError("fetch_macro is not implemented in Mission C.")

    def fetch_snapshot(self, symbol: Symbol) -> MarketSnapshot:
        raise NotImplementedError("fetch_snapshot is not implemented in Mission C.")

    def fetch_news(self, symbol: Symbol, start: datetime, end: datetime) -> Sequence[NewsItem]:
        raise NotImplementedError("fetch_news is not implemented in Mission C.")
