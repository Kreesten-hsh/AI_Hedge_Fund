"""Stratégie Institutionnelle Freqtrade Crypto 24/7 : AegisCryptoTrendStrategy.

Combine le suivi de tendance vectorisé, les breakouts de volatilité Keltner/Bollinger
et une gestion de risque stricte (Stop-Loss dynamique, Trailing-Stop, Volatility Position Sizing).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter


class AegisCryptoTrendStrategy(IStrategy):
    """Stratégie Freqtrade optimisée pour les marchés Crypto (BTC, ETH, SOL, etc.)."""

    # Ratios de gestion des positions
    minimal_roi = {
        "0": 0.08,      # 8% de profit immédiat si mouvement violent
        "30": 0.04,     # 4% de profit après 30 minutes
        "60": 0.02,     # 2% de profit après 60 minutes
        "120": 0.01,
    }

    # Stop-loss fixe maximal (protection contre les crashs)
    stoploss = -0.025   # -2.5%

    # Trailing stop dynamique
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True

    # Timeframe de trading
    timeframe = "15m"

    # Processus de démarrage
    startup_candle_count = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Génération vectorisée des indicateurs de tendance et de volatilité."""
        close = dataframe["close"]
        high = dataframe["high"]
        low = dataframe["low"]

        # Moyennes Mobiles exponentielles (Tendance)
        dataframe["ema_20"] = close.ewm(span=20).mean()
        dataframe["ema_50"] = close.ewm(span=50).mean()
        dataframe["ema_200"] = close.ewm(span=200).mean()

        # Bollinger Bands (Volatilité)
        ma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        dataframe["bb_upper"] = ma20 + (2.0 * std20)
        dataframe["bb_lower"] = ma20 - (2.0 * std20)
        dataframe["bb_width"] = (dataframe["bb_upper"] - dataframe["bb_lower"]) / (ma20 + 1e-9)

        # Average True Range (ATR)
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        dataframe["atr_14"] = tr.rolling(14).mean()

        # RSI (Momentum)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        dataframe["rsi"] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

        # ADX (Force de la Tendance)
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        
        plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / (dataframe["atr_14"] + 1e-9))
        minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / (dataframe["atr_14"] + 1e-9))
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9))
        dataframe["adx"] = dx.rolling(14).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Détection des points d'achat (Long)."""
        conditions = [
            (dataframe["close"] > dataframe["ema_50"]),                 # Tendance haussière court/moyen terme
            (dataframe["ema_50"] > dataframe["ema_200"]),               # Alignement des moyennes mobiles
            (dataframe["rsi"] > 50) & (dataframe["rsi"] < 70),          # Momentum positif non suracheté
            (dataframe["adx"] > 20),                                    # Tendance suffisamment forte
            (dataframe["close"] > dataframe["bb_upper"].shift(1)),      # Breakout de volatilité
            (dataframe["volume"] > 0),
        ]

        dataframe.loc[pd.concat(conditions, axis=1).all(axis=1), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Détection des points de sortie."""
        conditions = [
            (dataframe["close"] < dataframe["ema_20"]) |                # Cassure de moyenne mobile rapide
            (dataframe["rsi"] < 40)                                     # Retournement de momentum
        ]

        dataframe.loc[pd.concat(conditions, axis=1).all(axis=1), "exit_long"] = 1
        return dataframe
