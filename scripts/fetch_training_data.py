"""Script pour extraire les données réelles d'entraînement et de démo.

- Indices Synthétiques Deriv (Crash 1000, Boom 1000) via DerivHistoricalData (WebSocket)
- Or (XAUUSD) via OpenBBDataProvider

Enregistre les jeux de données sous format Parquet dans `data/market_data/`.
"""

from __future__ import annotations

import os
import logging
from datetime import datetime, timezone, timedelta
import pandas as pd

from aegis_trade.providers.deriv.historical_data import DerivHistoricalData
from aegis_trade.infrastructure.data.providers.openbb_provider import OpenBBDataProvider
from aegis_trade.domain.core import Symbol, TimeFrame, AssetClass

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = "data/market_data"

# ~52 jours de M1. Profondeur choisie pour la puissance statistique de SIG-02 :
# à un horizon de 5 barres, 75000 barres laissent ~15000 fenêtres non
# chevauchantes, contre ~1000 avec les 5000 barres d'une requête unique. Coûte
# ~15 requêtes paginées (ADR 0021, qui renverse le passage en M15 de l'ADR 0020 :
# la cible de 5 minutes n'est pas représentable dans une barre de 15 minutes).
M1_TARGET_BARS = 75_000


def fetch_deriv_data():
    client = DerivHistoricalData()

    # 1. Crash 1000 Index (CRASH1000)
    symbol_name_crash = "CRASH1000"
    out_filename_crash = "crash1000.parquet"
    logger.info(f"Fetching Crash 1000 ({symbol_name_crash}) M1 candles (paginated)...")
    try:
        crash_df = client.fetch_candles_paginated_sync(
            symbol=symbol_name_crash, target_count=M1_TARGET_BARS, granularity=60
        )
        if not crash_df.empty:
            out_path = os.path.join(OUTPUT_DIR, out_filename_crash)
            crash_df.to_parquet(out_path, index=False)
            span = crash_df["timestamp"].max() - crash_df["timestamp"].min()
            logger.info(
                f"SECURITY CHECK: Symbol requested '{symbol_name_crash}' verified -> "
                f"Saved {len(crash_df)} rows spanning {span} to {out_path}"
            )
    except Exception as e:
        logger.error(f"Failed to fetch Crash 1000 data: {e}")

    # Le bloc M15 qui figurait ici est retiré : l'ADR 0021 renverse le choix du
    # M15 pour DATA-01. `crash1000_m15.parquet` reste sur disque, consommé par
    # `diagnose_cost_budget_by_horizon.py` pour la comparaison M1/M15 qui, elle,
    # reste valide — mais il n'est plus rafraîchi, n'étant plus une route
    # d'ingestion.

    # 2. Boom 1000 Index (BOOM1000)
    symbol_name = "BOOM1000"
    out_filename = "boom1000.parquet"
    logger.info(f"Fetching Boom 1000 ({symbol_name}) M1 candles (paginated)...")
    try:
        boom_df = client.fetch_candles_paginated_sync(
            symbol=symbol_name, target_count=M1_TARGET_BARS, granularity=60
        )
        if not boom_df.empty:
            out_path = os.path.join(OUTPUT_DIR, out_filename)
            boom_df.to_parquet(out_path, index=False)
            span = boom_df["timestamp"].max() - boom_df["timestamp"].min()
            logger.info(
                f"SECURITY CHECK: Symbol requested '{symbol_name}' verified -> "
                f"Saved {len(boom_df)} rows spanning {span} to {out_path}"
            )
    except Exception as e:
        logger.error(f"Failed to fetch Boom 1000 data: {e}")

def fetch_gold_data():
    logger.info("Fetching XAUUSD (Gold) data via OpenBB...")
    try:
        provider = OpenBBDataProvider()
        gold_symbol = Symbol(name="XAUUSD", asset_class=AssetClass.COMMODITIES)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=180)
        
        bars = provider.fetch_ohlcv(gold_symbol, TimeFrame.D1, start_date, end_date)
        if bars:
            records = [
                {
                    "timestamp": b.timestamp,
                    "open": float(b.open),
                    "high": float(b.high),
                    "low": float(b.low),
                    "close": float(b.close),
                    "volume": float(b.volume)
                }
                for b in bars
            ]
            gold_df = pd.DataFrame(records)
            out_path = os.path.join(OUTPUT_DIR, "xauusd.parquet")
            gold_df.to_parquet(out_path, index=False)
            logger.info(f"Saved {len(gold_df)} rows to {out_path}")
        else:
            logger.warning("OpenBB returned 0 bars for XAUUSD.")
    except Exception as e:
        logger.error(f"Failed to fetch Gold data via OpenBB: {e}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fetch_deriv_data()
    fetch_gold_data()
    logger.info("Data fetching pipeline completed.")

if __name__ == "__main__":
    main()
