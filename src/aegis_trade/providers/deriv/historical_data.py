"""Adaptateur pour récupérer l'historique de bougies (candles) Deriv via WebSocket.

Utilise `websockets` directement sans dépendance lourde vers `python-deriv-api`.
Fournit les données historiques nécessaires au fine-tuning et aux backtests
sur les indices synthétiques (Crash 1000, Boom 1000, etc.).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
import pandas as pd

import websockets

logger = logging.getLogger(__name__)

DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"

class DerivHistoricalData:
    """Récupère l'historique de prix (candles) auprès de l'API Deriv."""

    def __init__(self, app_id: int = 1089, ws_url: str | None = None) -> None:
        self.app_id = app_id
        self.ws_url = ws_url or f"wss://ws.derivws.com/websockets/v3?app_id={app_id}"

    async def fetch_candles(
        self,
        symbol: str = "1HZ200V",  # Crash 1000 Index
        count: int = 5000,
        granularity: int = 60  # 60s = M1
    ) -> pd.DataFrame:
        """Récupère les bougies historiques depuis l'API WebSocket Deriv.

        :param symbol: Nom du symbole Deriv (ex: '1HZ200V' pour Crash 1000, '1HZ100V' pour Boom 1000)
        :param count: Nombre de bougies demandées (max 5000)
        :param granularity: Granularité en secondes (60, 120, 180, 300, 600, 900, 1800, 3600, 7200, 14400, 28800, 86400)
        :return: DataFrame pandas avec colonnes ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        """
        request_payload = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "granularity": granularity,
            "style": "candles"
        }

        logger.info(f"DerivHistoricalData: fetching {count} candles for {symbol} (granularity={granularity}s)...")

        async with websockets.connect(self.ws_url) as ws:
            await ws.send(json.dumps(request_payload))
            raw_response = await ws.recv()

            text = raw_response.decode("utf-8") if isinstance(raw_response, bytes) else raw_response
            data = json.loads(text)

            if "error" in data:
                error_msg = data["error"].get("message", str(data["error"]))
                raise RuntimeError(f"Deriv API error for {symbol}: {error_msg}")

            candles = data.get("candles", [])
            if not candles:
                logger.warning(f"Deriv returned no candles for {symbol}")
                return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            records = []
            for c in candles:
                records.append({
                    "timestamp": datetime.fromtimestamp(float(c["epoch"]), tz=timezone.utc),
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"]),
                    "volume": float(c.get("volume", 0.0))
                })

            df = pd.DataFrame(records)
            logger.info(f"DerivHistoricalData: successfully retrieved {len(df)} candles for {symbol}.")
            return df

    def fetch_candles_sync(
        self,
        symbol: str = "1HZ200V",
        count: int = 5000,
        granularity: int = 60
    ) -> pd.DataFrame:
        """Wrapper synchrone pour les scripts d'extraction."""
        return asyncio.run(self.fetch_candles(symbol=symbol, count=count, granularity=granularity))
