import numpy as np
import pandas as pd
from typing import List, Sequence

from aegis_trade.domain.core import MarketBar
from aegis_trade.domain.features import FeatureSet, FeatureMetadata, FeatureGroup
from aegis_trade.domain.ports.features import IFeatureExtractor


class TechnicalFeatureExtractor(IFeatureExtractor):
    """
    Extracts core technical features using standard pandas and numpy vectorization.
    Does NOT depend on pandas-ta or TA-Lib to maintain sovereignty.
    """

    def __init__(self) -> None:
        self._metadata: List[FeatureMetadata] = self._build_metadata()

    def _build_metadata(self) -> List[FeatureMetadata]:
        meta = []
        
        # Returns
        meta.extend([
            FeatureMetadata("return_1d", "1-period simple return", FeatureGroup.RETURNS, {}),
            FeatureMetadata("return_5d", "5-period simple return", FeatureGroup.RETURNS, {}),
            FeatureMetadata("return_10d", "10-period simple return", FeatureGroup.RETURNS, {}),
            FeatureMetadata("log_return", "1-period logarithmic return", FeatureGroup.RETURNS, {}),
        ])

        # Trend (EMAs)
        for p in [10, 20, 50, 100, 200]:
            meta.append(FeatureMetadata(f"ema_{p}", f"{p}-period Exponential Moving Average", FeatureGroup.TREND, {"period": p}))

        # Relative gap to the EMA 50. Read by the reflection pipeline, which
        # puts it on an axis of the Experience embedding: a constant there makes
        # a third of the clustering space inert, and DBSCAN feeds the patterns
        # the PatternAgent votes on.
        meta.append(FeatureMetadata("ema_distance", "Relative distance from close to EMA 50", FeatureGroup.TREND, {"period": 50}))

        # Momentum
        meta.extend([
            FeatureMetadata("rsi_14", "14-period Relative Strength Index", FeatureGroup.MOMENTUM, {"period": 14}),
            FeatureMetadata("macd", "MACD Line (12, 26)", FeatureGroup.MOMENTUM, {"fast": 12, "slow": 26}),
            FeatureMetadata("macd_signal", "MACD Signal Line (9)", FeatureGroup.MOMENTUM, {"period": 9}),
            FeatureMetadata("macd_hist", "MACD Histogram", FeatureGroup.MOMENTUM, {}),
        ])

        # Volatility
        meta.extend([
            FeatureMetadata("atr_14", "14-period Average True Range", FeatureGroup.VOLATILITY, {"period": 14}),
            FeatureMetadata("std_20", "20-period Rolling Standard Deviation", FeatureGroup.VOLATILITY, {"period": 20}),
            FeatureMetadata("hist_vol_20", "20-period Historical Volatility (annualized)", FeatureGroup.VOLATILITY, {"period": 20, "trading_days": 252}),
            FeatureMetadata("bb_middle", "Bollinger middle band (20-period SMA)", FeatureGroup.VOLATILITY, {"period": 20}),
            FeatureMetadata("bb_upper", "Bollinger upper band (SMA + 2 std)", FeatureGroup.VOLATILITY, {"period": 20, "std_dev": 2.0}),
            FeatureMetadata("bb_lower", "Bollinger lower band (SMA - 2 std)", FeatureGroup.VOLATILITY, {"period": 20, "std_dev": 2.0}),
        ])

        # Volume
        meta.extend([
            FeatureMetadata("volume_sma_20", "20-period Volume Simple Moving Average", FeatureGroup.VOLUME, {"period": 20}),
            FeatureMetadata("rel_volume", "Relative Volume (Volume / Volume SMA)", FeatureGroup.VOLUME, {"period": 20}),
        ])

        # Price
        meta.extend([
            FeatureMetadata("typical_price", "(High + Low + Close) / 3", FeatureGroup.PRICE, {}),
            FeatureMetadata("median_price", "(High + Low) / 2", FeatureGroup.PRICE, {}),
            FeatureMetadata("vwap", "Volume Weighted Average Price (Cumulative)", FeatureGroup.PRICE, {}),
        ])
        
        return meta

    def get_metadata(self) -> List[FeatureMetadata]:
        return self._metadata

    def extract(self, bars: Sequence[MarketBar]) -> List[FeatureSet]:
        if not bars:
            return []

        # 1. Sort the bars themselves, not just the DataFrame. The reconstruction
        # step reads back from this list positionally: sorting only the frame
        # would attach a row's features to another bar's timestamp and symbol.
        ordered_bars = sorted(bars, key=lambda b: b.timestamp)

        df = pd.DataFrame([
            {
                "timestamp": b.timestamp,
                "open": float(b.open),
                "high": float(b.high),
                "low": float(b.low),
                "close": float(b.close),
                "volume": float(b.volume)
            }
            for b in ordered_bars
        ])

        # Base series
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']

        # 2. Returns
        df['return_1d'] = close.pct_change(1)
        df['return_5d'] = close.pct_change(5)
        df['return_10d'] = close.pct_change(10)
        df['log_return'] = np.log(close / close.shift(1))

        # 3. Trend (EMA)
        for p in [10, 20, 50, 100, 200]:
            df[f'ema_{p}'] = close.ewm(span=p, adjust=False).mean()

        # Derived from the EMA 50 already computed above rather than from a
        # second average: two trend measures in the same FeatureSet could
        # disagree, and both travel with the order to the audit trail.
        df['ema_distance'] = (close - df['ema_50']) / df['ema_50']
        df['ema_distance'] = df['ema_distance'].replace([np.inf, -np.inf], np.nan)

        # 4. Momentum (RSI & MACD)
        # RSI 14
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        # Wilder's smoothing (exponential MA with alpha = 1/period)
        avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        df['rsi_14'] = df['rsi_14'].replace([np.inf, -np.inf], np.nan)

        # MACD (12, 26, 9)
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # 5. Volatility (ATR 14, Std 20, Historical Volatility)
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr_14'] = tr.ewm(alpha=1/14, adjust=False).mean()
        
        df['std_20'] = close.rolling(window=20).std()
        df['hist_vol_20'] = df['log_return'].rolling(window=20).std() * np.sqrt(252)

        # Bollinger Bands (20, 2). Derived from std_20 rather than a second
        # dispersion computation: two measures of spread in the same FeatureSet
        # could disagree, and the VolatilityAgent votes on these bands.
        df['bb_middle'] = close.rolling(window=20).mean()
        df['bb_upper'] = df['bb_middle'] + 2.0 * df['std_20']
        df['bb_lower'] = df['bb_middle'] - 2.0 * df['std_20']

        # 6. Volume
        df['volume_sma_20'] = volume.rolling(window=20).mean()
        df['rel_volume'] = volume / df['volume_sma_20']
        df['rel_volume'] = df['rel_volume'].replace([np.inf, -np.inf], np.nan)

        # 7. Price
        df['typical_price'] = (high + low + close) / 3
        df['median_price'] = (high + low) / 2
        
        # VWAP (Cumulative from the beginning of the series)
        # Note: In intraday trading, VWAP usually resets daily. For continuous daily data,
        # it is often computed as a rolling window or session cumulative. 
        # Here we compute it over the provided sequence.
        cum_vol = volume.cumsum()
        cum_vol_price = (df['typical_price'] * volume).cumsum()
        df['vwap'] = cum_vol_price / cum_vol
        df['vwap'] = df['vwap'].replace([np.inf, -np.inf], np.nan)

        # 8. Reconstruct FeatureSets
        feature_names = [m.name for m in self._metadata]

        # Column-wise extraction rather than df.iterrows(): row-by-row pandas
        # indexing cost ~390ms per call on a 200-bar window, well past the
        # Council's 20ms decision budget, and the extractor runs before the vote.
        columns = {
            name: [None if pd.isna(v) else float(v) for v in df[name].to_numpy()]
            for name in feature_names
        }

        feature_sets = []
        for i, bar in enumerate(ordered_bars):
            row_dict = {name: values[i] for name, values in columns.items()}

            fs = FeatureSet(
                symbol=bar.symbol,
                timeframe=bar.timeframe,
                timestamp=bar.timestamp,
                features=row_dict
            )
            feature_sets.append(fs)

        return feature_sets
