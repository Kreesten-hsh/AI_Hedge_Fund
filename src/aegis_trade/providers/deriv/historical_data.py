"""Adaptateur pour récupérer l'historique de bougies (candles) Deriv via WebSocket.

Utilise `websockets` directement sans dépendance lourde vers `python-deriv-api`.
Fournit les données historiques nécessaires au fine-tuning et aux backtests
sur les indices synthétiques (Crash 1000, Boom 1000, etc.) et les commodities (Gold frxXAUUSD).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, time, timedelta, timezone
from typing import Protocol

import pandas as pd  # type: ignore
import websockets

logger = logging.getLogger(__name__)

DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"

# Plafond serveur maximal autorisé par la méthode (5000).
MAX_CANDLES_PER_REQUEST = 5000

_CANDLE_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

RawCandle = dict[str, float]
CandleRecord = dict[str, datetime | float]


def _is_weekend_close(dt: datetime) -> bool:
    """Vérifie si un datetime UTC tombe pendant la fermeture de week-end (samedi/dimanche ou vendredi soir >= 21:00 UTC).

    Sur l'API Deriv WebSocket pour frxXAUUSD, le marché ferme le vendredi à 20:55:00 UTC
    et rouvre le lundi à 00:00:00 UTC (vérifié par mesures brutes minute par minute).
    """
    wd = dt.weekday()
    if wd == 5:  # Samedi
        return True
    if wd == 6:  # Dimanche (fermé 24h sur Deriv pour Gold, réouverture Lundi 00:00 UTC)
        return True
    if wd == 4 and (dt.hour > 21 or (dt.hour == 21 and dt.minute >= 0)):  # Vendredi >= 21:00 UTC
        return True
    return False


def _snap_to_friday_close(dt: datetime) -> datetime:
    """Ramène un datetime situé pendant le week-end au vendredi précédent à 20:59:00 UTC."""
    wd = dt.weekday()
    if wd == 5:  # Samedi -> 1 jour avant
        days_back = 1
    elif wd == 6:  # Dimanche -> 2 jours avant
        days_back = 2
    elif wd == 4:  # Vendredi soir -> même jour
        days_back = 0
    else:
        days_back = (wd + 2) % 7

    target_date = dt.date() - timedelta(days=days_back)
    return datetime.combine(target_date, time(20, 59, 0), tzinfo=timezone.utc)


class _WebSocketLike(Protocol):
    async def send(self, message: str) -> None: ...
    async def recv(self) -> str | bytes: ...


def _candles_to_records(candles: list[RawCandle]) -> list[CandleRecord]:
    """Bougies brutes de l'API -> lignes typées, prêtes pour un DataFrame."""
    return [
        {
            "timestamp": datetime.fromtimestamp(float(c["epoch"]), tz=timezone.utc),
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
            "volume": float(c.get("volume", 0.0)),
        }
        for c in candles
    ]


class DerivHistoricalData:
    """Récupère l'historique de prix (candles) auprès de l'API Deriv."""

    def __init__(self, app_id: int = 1089, ws_url: str | None = None) -> None:
        self.app_id = app_id
        self.ws_url = ws_url or f"wss://ws.derivws.com/websockets/v3?app_id={app_id}"

    async def fetch_candles(
        self,
        symbol: str = "CRASH1000",
        count: int = 5000,
        granularity: int = 60,
    ) -> pd.DataFrame:
        """Récupère les bougies historiques depuis l'API WebSocket Deriv."""
        request_payload = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "granularity": granularity,
            "style": "candles",
        }

        logger.info(
            f"DerivHistoricalData: fetching {count} candles for {symbol} (granularity={granularity}s)..."
        )

        async with websockets.connect(self.ws_url) as ws:
            await ws.send(json.dumps(request_payload))
            raw_response = await ws.recv()

            text = raw_response.decode("utf-8") if isinstance(raw_response, bytes) else raw_response
            data = json.loads(text)

            if "error" in data:
                error_msg = data["error"].get("message", str(data["error"]))
                raise RuntimeError(f"Deriv API error for {symbol}: {error_msg}")

            candles: list[RawCandle] = data.get("candles", [])
            if not candles:
                logger.warning(f"Deriv returned no candles for {symbol}")
                return pd.DataFrame(columns=_CANDLE_COLUMNS)

            df = pd.DataFrame(_candles_to_records(candles))
            logger.info(f"DerivHistoricalData: successfully retrieved {len(df)} candles for {symbol}.")
            return df

    def fetch_candles_sync(
        self,
        symbol: str = "CRASH1000",
        count: int = 5000,
        granularity: int = 60,
    ) -> pd.DataFrame:
        """Wrapper synchrone pour les scripts d'extraction."""
        return asyncio.run(self.fetch_candles(symbol=symbol, count=count, granularity=granularity))

    async def _fetch_candle_page(
        self,
        ws: _WebSocketLike,
        symbol: str,
        count: int,
        granularity: int,
        end: str,
    ) -> list[RawCandle]:
        """Un bloc de bougies se terminant à `end`, sur une connexion déjà ouverte."""
        await ws.send(
            json.dumps(
                {
                    "ticks_history": symbol,
                    "adjust_start_time": 1,
                    "count": count,
                    "end": end,
                    "granularity": granularity,
                    "style": "candles",
                }
            )
        )
        try:
            raw = await ws.recv()
        except ConnectionError:
            return []
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        data = json.loads(text)

        if "error" in data:
            message = data["error"].get("message", str(data["error"]))
            raise RuntimeError(f"Deriv API error for {symbol}: {message}")

        candles: list[RawCandle] = data.get("candles", [])
        return candles

    async def fetch_candles_paginated(
        self,
        symbol: str = "CRASH1000",
        target_count: int = 20_000,
        granularity: int = 60,
        page_size: int = MAX_CANDLES_PER_REQUEST,
    ) -> pd.DataFrame:
        """Historique profond, obtenu en reculant `end` bloc après bloc.

        La pagination lève la limite de 5000 bougies uniques par requête en reculant `end`
        sous la plus ancienne barre reçue et en gérant l'ancrage hebdomadaire/week-end.

        :param target_count: Nombre de bougies visé.
        :param page_size: Bougies par requête (max 5000).
        """
        if page_size > MAX_CANDLES_PER_REQUEST:
            raise ValueError(
                f"page_size {page_size} dépasse le plafond serveur de "
                f"{MAX_CANDLES_PER_REQUEST} : l'API renverrait "
                f"{MAX_CANDLES_PER_REQUEST} bougies sans le signaler, et tous les "
                "curseurs de pagination seraient décalés."
            )
        if page_size < 1 or target_count < 1 or granularity < 1:
            raise ValueError(
                f"page_size={page_size}, target_count={target_count} et "
                f"granularity={granularity} doivent être >= 1."
            )

        by_epoch: dict[int, CandleRecord] = {}
        end = "latest"

        async with websockets.connect(self.ws_url) as ws:
            while len(by_epoch) < target_count:
                candles = await self._fetch_candle_page(
                    ws, symbol, page_size, granularity, end
                )
                if not candles:
                    if end != "latest":
                        try:
                            curr_dt = datetime.fromtimestamp(int(end), tz=timezone.utc)
                            if _is_weekend_close(curr_dt):
                                snapped_dt = _snap_to_friday_close(curr_dt)
                                snapped_epoch = int(snapped_dt.timestamp())
                                if snapped_epoch < int(end):
                                    logger.info(
                                        "%s : curseur end=%s en week-end. Repositionnement sur vendredi %s.",
                                        symbol,
                                        end,
                                        snapped_dt,
                                    )
                                    end = str(snapped_epoch)
                                    continue
                        except ValueError:
                            pass
                    break

                before = len(by_epoch)
                for record, candle in zip(_candles_to_records(candles), candles):
                    by_epoch[int(candle["epoch"])] = record

                added = len(by_epoch) - before

                # Une page qui n'apporte aucune barre inédite signifie qu'on a atteint le début des données
                if added == 0:
                    logger.info(
                        "Historique %s épuisé à %d bougies (0 barre inédite reçue).",
                        symbol,
                        len(by_epoch),
                    )
                    break

                oldest_epoch = min(int(c["epoch"]) for c in candles)
                next_epoch = oldest_epoch - granularity
                next_dt = datetime.fromtimestamp(next_epoch, tz=timezone.utc)

                if _is_weekend_close(next_dt):
                    snapped_dt = _snap_to_friday_close(next_dt)
                    next_epoch = int(snapped_dt.timestamp())
                    logger.info(
                        "%s : Ancrage hebdomadaire -> saut de week-end de %s vers vendredi %s.",
                        symbol,
                        next_dt,
                        snapped_dt,
                    )

                end = str(next_epoch)
                logger.info(
                    "%s : %d bougies cumulées, prochaine page avant %s.",
                    symbol,
                    len(by_epoch),
                    end,
                )

        if not by_epoch:
            logger.warning("Deriv returned no candles for %s", symbol)
            return pd.DataFrame(columns=_CANDLE_COLUMNS)

        df = pd.DataFrame([by_epoch[e] for e in sorted(by_epoch)])
        df = df.iloc[-target_count:].reset_index(drop=True)
        logger.info(
            "DerivHistoricalData: %d bougies pour %s, de %s à %s.",
            len(df),
            symbol,
            df["timestamp"].iloc[0],
            df["timestamp"].iloc[-1],
        )
        return df

    def fetch_candles_paginated_sync(
        self,
        symbol: str = "CRASH1000",
        target_count: int = 20_000,
        granularity: int = 60,
        page_size: int = MAX_CANDLES_PER_REQUEST,
    ) -> pd.DataFrame:
        """Wrapper synchrone pour les scripts d'extraction."""
        return asyncio.run(
            self.fetch_candles_paginated(
                symbol=symbol,
                target_count=target_count,
                granularity=granularity,
                page_size=page_size,
            )
        )
