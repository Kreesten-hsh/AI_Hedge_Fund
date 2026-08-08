"""Tests du flux de ticks Deriv.

Le protocole est vérifié sur des messages Deriv réels (forme documentée de la
réponse `ticks`), avec une connexion doublée : aucun réseau, mais aucun
raccourci non plus sur le format.
"""

from __future__ import annotations

import json
from datetime import timezone
from decimal import Decimal
from typing import Any

import pytest

from aegis_trade.domain.core import AssetClass, Symbol
from aegis_trade.providers.deriv import DerivMarketGateway, DerivProtocolError

SYMBOL = Symbol(name="frxEURUSD", asset_class=AssetClass.FOREX)


class _FakeConnection:
    """Connexion WebSocket doublée : rejoue une file de messages."""

    def __init__(self, inbound: list[str]) -> None:
        self.inbound = list(inbound)
        self.sent: list[dict[str, Any]] = []
        self.closed = False

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    async def recv(self) -> str:
        if not self.inbound:
            raise ConnectionError("flux terminé")
        return self.inbound.pop(0)

    async def close(self) -> None:
        self.closed = True


def _tick_message(quote: float, bid: float, ask: float, epoch: int = 1_770_000_000) -> str:
    return json.dumps(
        {
            "echo_req": {"ticks": SYMBOL.name, "subscribe": 1},
            "msg_type": "tick",
            "tick": {
                "ask": ask,
                "bid": bid,
                "epoch": epoch,
                "id": "abc123",
                "pip_size": 5,
                "quote": quote,
                "symbol": SYMBOL.name,
            },
        }
    )


async def _gateway(messages: list[str]) -> tuple[DerivMarketGateway, _FakeConnection]:
    connection = _FakeConnection(messages)

    async def factory() -> _FakeConnection:
        return connection

    gateway = DerivMarketGateway(connection_factory=factory)
    await gateway.connect()
    await gateway.subscribe(SYMBOL)
    return gateway, connection


@pytest.mark.asyncio
async def test_subscribe_sends_deriv_protocol_frame() -> None:
    _, connection = await _gateway([])
    assert connection.sent == [{"ticks": SYMBOL.name, "subscribe": 1}]


@pytest.mark.asyncio
async def test_stream_yields_domain_ticks() -> None:
    gateway, _ = await _gateway(
        [
            _tick_message(quote=1.08551, bid=1.08549, ask=1.08553, epoch=1_770_000_000),
            _tick_message(quote=1.08560, bid=1.08558, ask=1.08562, epoch=1_770_000_001),
        ]
    )

    ticks = [tick async for tick in gateway.stream()]

    assert len(ticks) == 2
    assert ticks[0].symbol == SYMBOL
    assert ticks[0].bid == Decimal("1.08549")
    assert ticks[0].ask == Decimal("1.08553")
    assert ticks[0].timestamp.tzinfo == timezone.utc
    assert ticks[1].bid > ticks[0].bid


@pytest.mark.asyncio
async def test_non_tick_messages_are_ignored() -> None:
    gateway, _ = await _gateway(
        [
            json.dumps({"msg_type": "ping", "ping": "pong"}),
            _tick_message(quote=1.1, bid=1.09, ask=1.11),
        ]
    )

    ticks = [tick async for tick in gateway.stream()]
    assert len(ticks) == 1


@pytest.mark.asyncio
async def test_deriv_error_is_raised_not_swallowed() -> None:
    gateway, _ = await _gateway(
        [json.dumps({"error": {"code": "InvalidSymbol", "message": "Symbol inconnu"}})]
    )

    with pytest.raises(DerivProtocolError, match="InvalidSymbol"):
        [tick async for tick in gateway.stream()]


@pytest.mark.asyncio
async def test_tick_without_price_is_refused() -> None:
    """Un prix absent ne devient jamais une valeur par défaut."""
    broken = json.dumps(
        {"msg_type": "tick", "tick": {"epoch": 1_770_000_000, "symbol": SYMBOL.name}}
    )
    gateway, _ = await _gateway([broken])

    with pytest.raises(DerivProtocolError, match="bid"):
        [tick async for tick in gateway.stream()]


@pytest.mark.asyncio
async def test_tick_for_unsubscribed_symbol_is_refused() -> None:
    foreign = json.dumps(
        {
            "msg_type": "tick",
            "tick": {"epoch": 1_770_000_000, "symbol": "R_100", "bid": 1.0, "ask": 1.1},
        }
    )
    gateway, _ = await _gateway([foreign])

    with pytest.raises(DerivProtocolError, match="non souscrit"):
        [tick async for tick in gateway.stream()]


@pytest.mark.asyncio
async def test_stream_before_connect_is_refused() -> None:
    gateway = DerivMarketGateway()
    with pytest.raises(RuntimeError, match="non connecté"):
        [tick async for tick in gateway.stream()]


@pytest.mark.asyncio
async def test_disconnect_closes_and_is_idempotent() -> None:
    gateway, connection = await _gateway([])
    await gateway.disconnect()
    assert connection.closed is True
    assert gateway.is_connected is False
    await gateway.disconnect()
