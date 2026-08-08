"""Authentification locale et CORS de l'API de contrôle.

L'audit relevait quatre POST et un WebSocket ouverts sans jeton, avec
`allow_origins=["*"]` et `allow_credentials=True`. Ces tests fixent le
comportement attendu : toute route mutante et le flux WebSocket exigent le
jeton local, et aucune origine n'est acceptée en gros.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from aegis_trade.api.security import ALLOWED_WS_TOPICS, TOKEN_ENV_VAR, TOKEN_HEADER

TEST_TOKEN = "jeton-de-test-local"

# Les quatre routes mutantes exposées par l'API (`grep '@router.post'`).
MUTATING_ROUTES = [
    "/api/risk/kill-switch",
    "/api/system/strategy/demo/start",
    "/api/system/strategy/demo/stop",
    "/api/positions/EURUSD/close",
]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv(TOKEN_ENV_VAR, TEST_TOKEN)
    monkeypatch.setenv("AEGIS_ENV", "DEMO")
    from aegis_trade.api.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize("route", MUTATING_ROUTES)
def test_mutating_route_requires_token(client: TestClient, route: str) -> None:
    response = client.post(route)
    assert response.status_code == 401, (
        f"{route} accepte un POST sans jeton : le broker est pilotable "
        f"par n'importe quel processus local."
    )


@pytest.mark.parametrize("route", MUTATING_ROUTES)
def test_mutating_route_rejects_wrong_token(client: TestClient, route: str) -> None:
    response = client.post(route, headers={TOKEN_HEADER: "mauvais-jeton"})
    assert response.status_code == 401


def test_valid_token_is_not_rejected_by_auth(client: TestClient) -> None:
    """Le bon jeton passe l'authentification.

    On vérifie seulement que ce n'est plus un 401 : le code métier en aval peut
    légitimement répondre 404 (position inconnue) ou 500 (broker absent en test).
    """
    response = client.post(
        "/api/positions/INEXISTANT/close",
        headers={TOKEN_HEADER: TEST_TOKEN},
    )
    assert response.status_code != 401
    assert response.status_code == 404


def test_read_routes_stay_open_locally(client: TestClient) -> None:
    """La lecture reste libre : le jeton protège l'exécution, pas la supervision."""
    assert client.get("/").status_code == 200
    assert client.get("/api/system/health").status_code == 200


def test_cors_never_allows_wildcard_origin() -> None:
    from aegis_trade.api.security import allowed_origins

    origins = allowed_origins()
    assert "*" not in origins
    assert origins, "Une liste d'origines vide bloquerait le dashboard."


def test_cors_origins_are_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    from aegis_trade.api.security import allowed_origins

    monkeypatch.setenv("AEGIS_ALLOWED_ORIGINS", "http://a.local, http://b.local")
    assert allowed_origins() == ["http://a.local", "http://b.local"]


def test_websocket_requires_token(client: TestClient) -> None:
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/dashboard/portfolio") as ws:
            ws.receive_json()


def test_websocket_rejects_unknown_topic(client: TestClient) -> None:
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/dashboard/../../etc?token={TEST_TOKEN}"
        ) as ws:
            ws.receive_json()


@pytest.mark.parametrize("topic", sorted(ALLOWED_WS_TOPICS))
def test_websocket_accepts_whitelisted_topics(client: TestClient, topic: str) -> None:
    with client.websocket_connect(f"/ws/dashboard/{topic}?token={TEST_TOKEN}") as ws:
        ws.send_text("ping")


def test_live_env_requires_explicit_consent(monkeypatch: pytest.MonkeyPatch) -> None:
    """`i_understand_this_is_real_money` ne peut pas venir d'un littéral."""
    import aegis_trade.api.deps as deps

    monkeypatch.setattr(deps, "_orchestrator", None)
    monkeypatch.setenv("AEGIS_ENV", "LIVE")
    monkeypatch.delenv("AEGIS_I_UNDERSTAND_THIS_IS_REAL_MONEY", raising=False)

    with pytest.raises(RuntimeError, match="AEGIS_I_UNDERSTAND_THIS_IS_REAL_MONEY"):
        deps.get_orchestrator()

    monkeypatch.setattr(deps, "_orchestrator", None)


def test_token_is_never_a_known_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sans configuration, le jeton est tiré au hasard — jamais une valeur devinable."""
    import aegis_trade.api.security as security

    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
    monkeypatch.setattr(security, "_ephemeral_token", None)
    generated = security.get_api_token()

    assert len(generated) >= 32
    assert generated not in {"", "aegis", "changeme", "token", "dummy"}
    assert security.get_api_token() == generated, "Le jeton doit être stable dans le process."

    monkeypatch.setattr(security, "_ephemeral_token", None)
