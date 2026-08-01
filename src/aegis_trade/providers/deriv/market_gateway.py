"""Abonnement aux ticks Deriv par WebSocket.

Implémente le protocole Deriv directement (`{"ticks": ..., "subscribe": 1}`)
plutôt que via le SDK `python-deriv-api` : le SDK expose des Observables RxPY
qu'il faudrait ponter vers asyncio, et il n'est pas installé dans cet
environnement. Le protocole tenant en trois messages, l'adaptateur direct est
plus simple à tester et ne fait entrer aucune dépendance supplémentaire.

Frontière : cette classe est le seul endroit du système qui voit un message
Deriv. Elle ne laisse sortir que des `Tick` du domaine.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Awaitable, Callable, Optional, Protocol

from aegis_trade.domain.core import Symbol, Tick
from aegis_trade.domain.ports.market_data import IMarketDataGateway

logger = logging.getLogger(__name__)

DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3"


class DerivProtocolError(Exception):
    """Réponse Deriv inexploitable.

    Levée plutôt qu'absorbée : un tick mal formé silencieusement ignoré
    ressemblerait, en aval, à un marché sans mouvement.
    """


class _Connection(Protocol):
    """Ce que l'adaptateur attend d'une connexion WebSocket."""

    async def send(self, message: str) -> None: ...

    async def recv(self) -> str | bytes: ...

    async def close(self) -> None: ...


ConnectionFactory = Callable[[], Awaitable[_Connection]]


async def _default_connection_factory() -> _Connection:
    import websockets

    return await websockets.connect(DERIV_WS_URL)  # type: ignore[return-value]


class DerivMarketGateway(IMarketDataGateway):
    """Flux de ticks Deriv, converti en `Tick` du domaine."""

    def __init__(
        self,
        app_id: int = 1089,
        connection_factory: Optional[ConnectionFactory] = None,
    ) -> None:
        self._app_id = app_id
        self._connection_factory = connection_factory or _default_connection_factory
        self._connection: Optional[_Connection] = None
        # Deriv identifie les symboles par leur nom court ("R_50", "frxEURUSD") ;
        # le domaine par un `Symbol` complet. On garde la correspondance pour
        # reconstruire le `Symbol` d'origine à la réception, plutôt que d'en
        # fabriquer un approximatif à partir du texte reçu.
        self._subscribed: dict[str, Symbol] = {}

    @property
    def is_connected(self) -> bool:
        return self._connection is not None

    async def connect(self) -> None:
        if self._connection is not None:
            return
        self._connection = await self._connection_factory()
        logger.info("DerivMarketGateway connecté (app_id=%s).", self._app_id)

    async def disconnect(self) -> None:
        connection = self._connection
        self._connection = None
        self._subscribed.clear()
        if connection is None:
            return
        await connection.close()
        logger.info("DerivMarketGateway déconnecté.")

    async def subscribe(self, symbol: Symbol) -> None:
        connection = self._require_connection()
        self._subscribed[symbol.name] = symbol
        await connection.send(json.dumps({"ticks": symbol.name, "subscribe": 1}))
        logger.info("Abonnement aux ticks Deriv : %s", symbol.name)

    def stream(self) -> AsyncIterator[Tick]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[Tick]:
        connection = self._require_connection()
        while True:
            try:
                raw = await connection.recv()
            except (asyncio.CancelledError, GeneratorExit):
                raise
            except Exception:
                # La connexion est tombée. On termine le flux au lieu de
                # boucler à vide : le consommateur doit voir la coupure.
                logger.exception("Flux de ticks Deriv interrompu.")
                return

            tick = self._parse_message(raw)
            if tick is not None:
                yield tick

    def _require_connection(self) -> _Connection:
        if self._connection is None:
            raise RuntimeError(
                "DerivMarketGateway non connecté : appeler `connect()` avant "
                "`subscribe()` ou `stream()`."
            )
        return self._connection

    def _parse_message(self, raw: str | bytes) -> Optional[Tick]:
        """Traduit un message Deriv en `Tick`, ou `None` s'il n'en porte pas.

        Les messages hors ticks (réponses `ping`, accusés d'abonnement) sont
        ignorés silencieusement ; un message *de tick* mal formé, lui, lève.
        """
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        try:
            payload: Any = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DerivProtocolError(f"Message Deriv non JSON : {text[:200]}") from exc

        if not isinstance(payload, dict):
            raise DerivProtocolError(f"Message Deriv inattendu : {text[:200]}")

        if "error" in payload:
            error = payload["error"]
            code = error.get("code") if isinstance(error, dict) else None
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise DerivProtocolError(f"Erreur Deriv {code} : {message}")

        tick_payload = payload.get("tick")
        if not isinstance(tick_payload, dict):
            return None

        return self._to_domain_tick(tick_payload)

    def _to_domain_tick(self, tick_payload: dict[str, Any]) -> Tick:
        name = tick_payload.get("symbol")
        if not isinstance(name, str):
            raise DerivProtocolError("Tick Deriv sans symbole exploitable.")

        symbol = self._subscribed.get(name)
        if symbol is None:
            raise DerivProtocolError(
                f"Tick reçu pour un symbole non souscrit : {name}. "
                "Le flux ne doit contenir que ce qui a été demandé."
            )

        epoch = tick_payload.get("epoch")
        if not isinstance(epoch, (int, float)):
            raise DerivProtocolError(f"Tick {name} sans horodatage exploitable.")

        bid = self._to_decimal(tick_payload.get("bid"), name, "bid")
        ask = self._to_decimal(tick_payload.get("ask"), name, "ask")

        return Tick(
            symbol=symbol,
            timestamp=datetime.fromtimestamp(float(epoch), tz=timezone.utc),
            bid=bid,
            ask=ask,
        )

    @staticmethod
    def _to_decimal(value: Any, symbol_name: str, field: str) -> Decimal:
        if value is None:
            raise DerivProtocolError(
                f"Tick {symbol_name} sans `{field}`. Un prix absent n'est jamais "
                "remplacé par une valeur par défaut."
            )
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise DerivProtocolError(
                f"Tick {symbol_name} : `{field}` illisible ({value!r})."
            ) from exc
