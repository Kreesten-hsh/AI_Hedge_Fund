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
from typing import Protocol

import pandas as pd

import websockets

logger = logging.getLogger(__name__)

DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"

# Plafond serveur par requête `ticks_history`. Demander davantage ne produit pas
# d'erreur : le serveur renvoie 5000 en silence. C'est ce qui rend la pagination
# obligatoire pour tout historique plus profond, et c'est aussi pourquoi
# `fetch_candles_paginated` refuse un `page_size` supérieur — croire avancer par
# blocs de 20000 alors qu'on en reçoit 5000 décalerait tous les curseurs `end`.
MAX_CANDLES_PER_REQUEST = 5000

_CANDLE_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

# Bougie telle que l'API la renvoie. `epoch` est un entier, les autres champs des
# flottants ; `float` couvre les deux côté typage et la conversion explicite dans
# `_candles_to_records` reste la frontière de confiance avec le JSON reçu.
RawCandle = dict[str, float]

# Ligne prête pour pandas : un horodatage plus cinq flottants.
CandleRecord = dict[str, datetime | float]


class _WebSocketLike(Protocol):
    """Le strict nécessaire d'une connexion WebSocket pour paginer.

    Déclaré ici plutôt qu'en important un type concret de `websockets` : la
    bibliothèque a renommé sa classe de connexion entre versions majeures, et
    seule cette paire de méthodes est réellement utilisée.
    """

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
        symbol: str = "CRASH1000",  # Crash 1000 Index
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
        granularity: int = 60
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
        """Un bloc de bougies se terminant à `end`, sur une connexion déjà ouverte.

        Réutiliser la connexion entre les pages évite une poignée de main
        WebSocket par bloc : sur une quinzaine de requêtes, l'écart est net et le
        risque de limitation de débit plus faible.
        """
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
        raw = await ws.recv()
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

        `fetch_candles` est plafonné à 5000 bougies par le serveur, ce qui donne
        ~3.5 jours en M1. La pagination lève ce plafond sans changer de
        granularité — l'alternative (bougies plus grosses) impose une détention
        minimale égale à la taille de barre, ce qui est disqualifiant pour un
        horizon cible de quelques minutes (ADR 0021).

        :param target_count: Nombre de bougies visé. La méthode s'arrête avant si
            l'historique du symbole est épuisé.
        :param page_size: Bougies par requête, plafonné par le serveur.
        :raises ValueError: `page_size` au-dessus du plafond serveur, ou
            paramètres non positifs.
        :raises RuntimeError: erreur API en cours de route. L'exception remonte
            au lieu de renvoyer un historique partiel, qui passerait pour complet.
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

        # Indexé par epoch : Deriv peut renvoyer des barres déjà vues d'un bloc à
        # l'autre, et un doublon produit un rendement nul qui ressemble à une
        # vraie observation.
        by_epoch: dict[int, CandleRecord] = {}
        end = "latest"

        async with websockets.connect(self.ws_url) as ws:
            while len(by_epoch) < target_count:
                candles = await self._fetch_candle_page(
                    ws, symbol, page_size, granularity, end
                )
                if not candles:
                    break

                before = len(by_epoch)
                for record, candle in zip(_candles_to_records(candles), candles):
                    by_epoch[int(candle["epoch"])] = record

                # Un bloc qui apporte moins de barres inédites qu'une page pleine
                # signifie que le serveur a buté sur le début de son historique et
                # a resservi des barres déjà vues. Sans cette sortie, la boucle
                # martèlerait l'API jusqu'à target_count pour zéro donnée nouvelle.
                if len(by_epoch) - before < page_size:
                    logger.info(
                        "Historique %s épuisé à %d bougies (page incomplète en barres inédites).",
                        symbol,
                        len(by_epoch),
                    )
                    break

                # Reculer d'exactement une granularité sous la plus ancienne barre
                # reçue : réutiliser cette barre la renverrait en doublon, reculer
                # davantage ouvrirait un trou.
                oldest = min(int(c["epoch"]) for c in candles)
                end = str(oldest - granularity)
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
        # Troncature par la TÊTE : si un bloc dépasse la cible, ce sont les barres
        # les plus anciennes qu'on jette. Les plus récentes sont celles sur
        # lesquelles un modèle destiné à trader doit être validé.
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
