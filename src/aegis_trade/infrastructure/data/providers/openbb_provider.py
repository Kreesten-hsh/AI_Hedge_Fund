import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence
import pandas as pd
from openbb import obb
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from aegis_trade.domain.core import (
    Symbol,
    TimeFrame,
    MarketBar,
    EconomicIndicator,
    MarketSnapshot,
    NewsItem,
)
from aegis_trade.domain.ports.data_provider import IDataProvider
from aegis_trade.domain.exceptions.data import DataProviderError
from aegis_trade.infrastructure.data.mappers.openbb_mapper import OpenBBMapper

logger = logging.getLogger(__name__)


class OpenBBDataProvider(IDataProvider):
    """
    Implementation of IDataProvider using OpenBB (v4).
    Returns purely domain objects and handles API errors securely with retries.
    Uses openbb-fred extension for macro economic series with fallback to FRED direct CSV.
    """

    def __init__(self, default_provider: str = "yfinance", timeout: int = 15):
        self.default_provider = default_provider
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DataProviderError),
        reraise=True,
    )
    def fetch_ohlcv(
        self, symbol: Symbol, timeframe: TimeFrame, start: datetime, end: datetime
    ) -> Sequence[MarketBar]:
        
        interval_map = {
            TimeFrame.M1: "1m",
            TimeFrame.M5: "5m",
            TimeFrame.M15: "15m",
            TimeFrame.M30: "30m",
            TimeFrame.H1: "1h",
            TimeFrame.H4: "1d",
            TimeFrame.D1: "1d",
        }
        interval = interval_map.get(timeframe, "1d")
        
        ticker_map = {
            "DXY": "DX-Y.NYB",
            "US10Y": "^TNX",
            "XAUUSD": "GC=F",
            "GOLD": "GC=F",
        }
        target_ticker = ticker_map.get(symbol.name, symbol.name)
        
        try:
            if symbol.name in ["DXY", "US10Y"]:
                res = obb.index.price.historical(  # type: ignore[union-attr]
                    symbol=target_ticker,
                    provider=self.default_provider,
                    interval=interval,
                    start_date=start.strftime("%Y-%m-%d"),
                    end_date=end.strftime("%Y-%m-%d"),
                    timeout=self.timeout,
                )
            else:
                res = obb.equity.price.historical(  # type: ignore[union-attr]
                    symbol=target_ticker,
                    provider=self.default_provider,
                    interval=interval,
                    start_date=start.strftime("%Y-%m-%d"),
                    end_date=end.strftime("%Y-%m-%d"),
                    timeout=self.timeout,
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

    def _fetch_fred_csv_fallback(
        self, series_id: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Fallback direct CSV depuis St. Louis Fed sans clé d'API."""
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        df = pd.read_csv(url)
        df["observation_date"] = pd.to_datetime(df["observation_date"])
        df.set_index("observation_date", inplace=True)
        # Filtrer la plage de dates
        df = df.loc[(df.index >= pd.to_datetime(start.strftime("%Y-%m-%d"))) & 
                    (df.index <= pd.to_datetime(end.strftime("%Y-%m-%d")))]
        # Remplacer les valeurs non numériques (ex: '.') par NaN
        df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
        df.dropna(inplace=True)
        df.rename(columns={series_id: "value"}, inplace=True)
        return df

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DataProviderError),
        reraise=True,
    )
    def fetch_macro(
        self, symbol: Symbol, start: datetime, end: datetime
    ) -> Sequence[EconomicIndicator]:
        """Récupère des séries économiques (ex: DFII10 pour les Taux Réels) via openbb-fred ou fallback direct CSV FRED."""
        fred_ticker_map = {
            "REAL_RATE_10Y": "DFII10",
        }
        series_id = fred_ticker_map.get(symbol.name, symbol.name)
        
        df = pd.DataFrame()
        try:
            res = obb.economy.fred_series(  # type: ignore[union-attr]
                symbol=series_id,
                provider="fred",
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
                timeout=self.timeout,
            )
            df = res.to_df()
        except Exception as e:
            logger.info(f"OpenBB FRED sans clé API, bascule sur le fallback public CSV St. Louis Fed pour {series_id}...")
            try:
                df = self._fetch_fred_csv_fallback(series_id, start, end)
            except Exception as fallback_err:
                logger.error(f"Échec du fallback CSV FRED pour {series_id}: {fallback_err}")
                raise DataProviderError(f"FRED API/CSV Error: {fallback_err}") from fallback_err

        if df.empty:
            logger.warning(f"FRED returned empty data for {symbol.name} ({start} - {end})")
            return []

        indicators: list[EconomicIndicator] = []
        for index, row in df.iterrows():
            try:
                dt = index if isinstance(index, datetime) else datetime.fromisoformat(str(index))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                
                col_val = row.get("value", row.iloc[0] if len(row) > 0 else None)
                if col_val is None or str(col_val).lower() == "nan":
                    continue

                indicators.append(
                    EconomicIndicator(
                        symbol=symbol,
                        timestamp=dt,
                        value=Decimal(str(col_val)),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to map macro row for {symbol.name} at {index}: {e}")
        return indicators

    def fetch_snapshot(self, symbol: Symbol) -> MarketSnapshot:
        raise NotImplementedError("fetch_snapshot is not implemented.")

    def fetch_news(self, symbol: Symbol, start: datetime, end: datetime) -> Sequence[NewsItem]:
        raise NotImplementedError("fetch_news is not implemented.")
