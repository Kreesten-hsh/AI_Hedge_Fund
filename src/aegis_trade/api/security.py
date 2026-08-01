"""Authentification locale de l'API de contrôle.

Cette API pilote un broker : chaque route mutante peut ouvrir ou fermer une
position, ou déclencher le kill switch. Un port ouvert sans jeton suffit donc à
liquider un compte depuis n'importe quel processus de la machine, d'où un jeton
obligatoire sur tout POST **et** sur le WebSocket.

Le jeton vient de `AEGIS_API_TOKEN`. À défaut, un jeton éphémère est tiré au
premier besoin et affiché une seule fois : on refuse d'exposer une valeur par
défaut connue, et on refuse aussi d'ouvrir sans jeton du tout.
"""

from __future__ import annotations

import hmac
import os
import secrets

from fastapi import Header, HTTPException, status

TOKEN_ENV_VAR = "AEGIS_API_TOKEN"
TOKEN_HEADER = "X-Aegis-Token"

# Seuls sujets diffusés par le MonitoringEngine (`application/monitoring/engine.py`).
# Borner la liste empêche un client d'ouvrir une infinité de files côté serveur
# en variant le segment d'URL.
ALLOWED_WS_TOPICS: frozenset[str] = frozenset(
    {"portfolio", "positions", "trades", "risk", "system"}
)

_ephemeral_token: str | None = None


def get_api_token() -> str:
    """Jeton attendu par l'API. Lu à chaque appel : les tests le pilotent par env."""
    global _ephemeral_token
    configured = os.environ.get(TOKEN_ENV_VAR, "").strip()
    if configured:
        return configured
    if _ephemeral_token is None:
        _ephemeral_token = secrets.token_urlsafe(32)
        print(
            f"[aegis] Jeton d'API local (éphémère, non persisté) : {_ephemeral_token}\n"
            f"[aegis] Fixer {TOKEN_ENV_VAR} pour un jeton stable entre redémarrages.",
            flush=True,
        )
    return _ephemeral_token


def token_is_valid(candidate: str | None) -> bool:
    """Comparaison à temps constant. Un jeton absent est invalide, pas neutre."""
    if not candidate:
        return False
    return hmac.compare_digest(candidate, get_api_token())


def require_api_token(
    x_aegis_token: str | None = Header(default=None, alias=TOKEN_HEADER),
) -> None:
    """Dépendance FastAPI pour les routes mutantes."""
    if not token_is_valid(x_aegis_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Jeton local manquant ou invalide (en-tête {TOKEN_HEADER}).",
        )


def allowed_origins() -> list[str]:
    """Origines CORS explicites.

    Jamais `["*"]` : combiné à `allow_credentials=True`, il autoriserait
    n'importe quelle page web ouverte dans le navigateur de l'opérateur à
    piloter le broker.
    """
    configured = os.environ.get("AEGIS_ALLOWED_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
