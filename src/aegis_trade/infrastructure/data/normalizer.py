from typing import Sequence
from decimal import Decimal

from aegis_trade.domain.core import MarketBar
from aegis_trade.domain.exceptions.data import NormalizationError

class DataNormalizer:
    """
    Normalizes data formats to ensure consistency across the pipeline.
    """

    def normalize_ohlcv(self, bars: Sequence[MarketBar]) -> Sequence[MarketBar]:
        """
        Applies standard normalization to OHLCV data.
        For MarketBars, it ensures prices are rounded to standard precision,
        and zero volumes are handled appropriately if necessary.
        """
        try:
            normalized_bars = []
            for bar in bars:
                # E.g., round to 8 decimal places max for typical assets
                n_open = round(bar.open, 8)
                n_high = round(bar.high, 8)
                n_low = round(bar.low, 8)
                n_close = round(bar.close, 8)
                n_volume = round(bar.volume, 8)
                
                normalized_bars.append(
                    MarketBar(
                        symbol=bar.symbol,
                        timeframe=bar.timeframe,
                        timestamp=bar.timestamp,
                        open=n_open,
                        high=n_high,
                        low=n_low,
                        close=n_close,
                        volume=n_volume
                    )
                )
            return normalized_bars
        except Exception as e:
            raise NormalizationError(f"Failed to normalize MarketBars: {e}") from e
