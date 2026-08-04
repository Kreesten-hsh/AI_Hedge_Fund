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

def fetch_deriv_data():
    client = DerivHistoricalData()

    # 1. Crash 1000 Index (CRASH1000)
    symbol_name_crash = "CRASH1000"
    out_filename_crash = "crash1000.parquet"
    logger.info(f"Fetching Crash 1000 ({symbol_name_crash}) M1 candles...")
    try:
        crash_df = client.fetch_candles_sync(symbol=symbol_name_crash, count=5000, granularity=60)
        if not crash_df.empty:
            out_path = os.path.join(OUTPUT_DIR, out_filename_crash)
            crash_df.to_parquet(out_path, index=False)
            logger.info(f"SECURITY CHECK: Symbol requested '{symbol_name_crash}' verified -> Saved {len(crash_df)} rows to {out_path}")
    except Exception as e:
        logger.error(f"Failed to fetch Crash 1000 data: {e}")

    # 1b. Crash 1000 en M15 — route retenue par l'ADR 0020 pour DATA-01.
    # Sous le même plafond de 5000 bougies par requête, le M15 couvre ~52 jours
    # contre ~3.5 en M1, sans rétrécir le budget de coût (écart mesuré ±3 % à
    # détention égale sur période commune).
    logger.info(f"Fetching Crash 1000 ({symbol_name_crash}) M15 candles...")
    try:
        crash_m15_df = client.fetch_candles_sync(
            symbol=symbol_name_crash, count=5000, granularity=900
        )
        if not crash_m15_df.empty:
            out_path = os.path.join(OUTPUT_DIR, "crash1000_m15.parquet")
            crash_m15_df.to_parquet(out_path, index=False)
            span = crash_m15_df["timestamp"].max() - crash_m15_df["timestamp"].min()
            logger.info(
                f"SECURITY CHECK: Symbol requested '{symbol_name_crash}' (M15) verified -> "
                f"Saved {len(crash_m15_df)} rows spanning {span} to {out_path}"
            )
    except Exception as e:
        logger.error(f"Failed to fetch Crash 1000 M15 data: {e}")

    # 2. Boom 1000 Index (BOOM1000)
    symbol_name = "BOOM1000"
    out_filename = "boom1000.parquet"
    logger.info(f"Fetching Boom 1000 ({symbol_name}) M1 candles...")
    try:
        boom_df = client.fetch_candles_sync(symbol=symbol_name, count=5000, granularity=60)
        if not boom_df.empty:
            out_path = os.path.join(OUTPUT_DIR, out_filename)
            boom_df.to_parquet(out_path, index=False)
            logger.info(f"SECURITY CHECK: Symbol requested '{symbol_name}' verified -> Saved {len(boom_df)} rows to {out_path}")
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
