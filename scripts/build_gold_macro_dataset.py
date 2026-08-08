"""Construit le dataset combiné Gold M1 + Features Macroéconomiques FRED.

Extrait les séries macro (DFII10 Taux Réel 10 ans, DXY Index) via OpenBBDataProvider
et les aligne de manière causale (forward fill sans look-ahead bias) sur l'historique 75k barres M1 Gold.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from aegis_trade.domain.core import AssetClass, Symbol
from aegis_trade.infrastructure.data.providers.openbb_provider import OpenBBDataProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_macro_features(
    parquet_path: str = "data/market_data/xauusd.parquet",
    output_path: str = "data/market_data/xauusd_macro.parquet",
) -> pd.DataFrame:
    logger.info(f"Chargement du dataset Gold M1 depuis {parquet_path}...")
    df_gold = pd.read_parquet(parquet_path)
    
    # Assurer un format datetime UTC propre
    if not isinstance(df_gold.index, pd.DatetimeIndex):
        if "timestamp" in df_gold.columns:
            df_gold["timestamp"] = pd.to_datetime(df_gold["timestamp"], utc=True)
            df_gold.set_index("timestamp", inplace=True)
        else:
            df_gold.index = pd.to_datetime(df_gold.index, utc=True)
            
    df_gold.sort_index(inplace=True)
    
    start_dt = df_gold.index.min().to_pydatetime()
    end_dt = df_gold.index.max().to_pydatetime()
    logger.info(f"Plage Gold: {start_dt} à {end_dt} ({len(df_gold)} barres M1)")

    # Extraction des séries macro via OpenBBDataProvider
    provider = OpenBBDataProvider()
    
    macro_series: dict[str, pd.Series] = {}
    
    # 1. Taux Réel 10 ans FRED (DFII10)
    logger.info("Extraction de la série FRED DFII10 (Taux Réel 10 ans US)...")
    try:
        symbol_dfii10 = Symbol(name="DFII10", asset_class=AssetClass.INDICES)
        indicators_dfii10 = provider.fetch_macro(symbol_dfii10, start=start_dt, end=end_dt)
        if indicators_dfii10:
            ts_list = [ind.timestamp for ind in indicators_dfii10]
            val_list = [float(ind.value) for ind in indicators_dfii10]
            s_dfii10 = pd.Series(val_list, index=pd.to_datetime(ts_list, utc=True), name="dfii10")
            s_dfii10 = s_dfii10[~s_dfii10.index.duplicated(keep="last")].sort_index()
            macro_series["dfii10"] = s_dfii10
            logger.info(f"DFII10 récupéré: {len(s_dfii10)} points de données.")
        else:
            logger.warning("Aucune donnée retournée pour DFII10.")
    except Exception as e:
        logger.error(f"Échec de l'extraction FRED DFII10: {e}")

    # 2. Dollar Index (DXY)
    logger.info("Extraction du Dollar Index (DXY)...")
    try:
        symbol_dxy = Symbol(name="DXY", asset_class=AssetClass.INDICES)
        bars_dxy = provider.fetch_ohlcv(symbol_dxy, timeframe=pd.Timedelta("1d"), start=start_dt, end=end_dt)
        if bars_dxy:
            ts_list = [bar.timestamp for bar in bars_dxy]
            val_list = [float(bar.close) for bar in bars_dxy]
            s_dxy = pd.Series(val_list, index=pd.to_datetime(ts_list, utc=True), name="dxy")
            s_dxy = s_dxy[~s_dxy.index.duplicated(keep="last")].sort_index()
            macro_series["dxy"] = s_dxy
            logger.info(f"DXY récupéré: {len(s_dxy)} points de données.")
        else:
            logger.warning("Aucune donnée retournée pour DXY.")
    except Exception as e:
        logger.error(f"Échec de l'extraction DXY: {e}")

    # Alignement causal sur les barres M1 Gold
    df_combined = df_gold.copy()
    
    for name, series in macro_series.items():
        # Pour éviter le look-ahead bias, on décale les séries macro quotidiennes d'un jour (shift 1)
        # de manière à n'utiliser le niveau quotidien clôturé qu'au jour suivant M1.
        series_lagged = series.shift(1)
        
        # Re-échantillonnage et forward fill sur le temps M1
        aligned_series = series_lagged.reindex(df_combined.index, method="ffill")
        
        df_combined[f"macro_{name}"] = aligned_series
        
        # Variations et features dérivées macro
        # Variation 1 jour
        df_combined[f"feature_macro_{name}_change_1d"] = aligned_series.diff(1440)
        # Variation 5 jours
        df_combined[f"feature_macro_{name}_change_5d"] = aligned_series.diff(7200)

    # Remplir les NA de début de série propres
    df_combined.ffill(inplace=True)
    df_combined.bfill(inplace=True)
    
    if "timestamp" not in df_combined.columns:
        df_combined.reset_index(inplace=True)
        if "index" in df_combined.columns and "timestamp" not in df_combined.columns:
            df_combined.rename(columns={"index": "timestamp"}, inplace=True)
    
    logger.info(f"Enregistrement du dataset enrichi dans {output_path}...")
    df_combined.to_parquet(output_path)
    logger.info(f"Dataset prêt. Colonnes: {list(df_combined.columns)}")
    return df_combined


if __name__ == "__main__":
    build_macro_features()
