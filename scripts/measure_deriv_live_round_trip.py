"""Aller-retours Multipliers automatisés sur compte démo Deriv, coût mesuré.

Ce script AUTOMATISE le protocole que l'ADR 0021 a exécuté à la main : ouvrir une
position Multipliers, la fermer quelques secondes plus tard, et déduire le péage
réel du P&L réalisé. Il existe pour lever la réserve explicite de COST-01 —
« mesure sur compte démo, 5 trades, une session, multiplicateur x100 seulement ».
Une mesure transcrite à la main n'est pas rejouable ; celle-ci l'est.

CE QU'IL AJOUTE À LA MESURE MANUELLE — la décomposition. Le relevé manuel ne
pouvait produire qu'un coût agrégé, parce que le prix au moment de la DÉCISION
n'était pas noté. Ici on relève le spot juste avant d'envoyer l'ordre, et le
contrat renvoie le spot réellement obtenu. L'écart est du slippage, et il est
séparé du péage :

    coût total payé = coût sur spots exécutés (commission) + slippage

Le chiffre de l'ADR 0021 (0.745 bps Crash, 1.063 bps Boom) est le PREMIER terme
seulement. Il ne faut donc pas s'attendre à ce que ce script le reproduise à
l'identique : s'il sort plus haut, c'est le second terme qui devient visible, pas
une contradiction.

FRONTIÈRE ARCHITECTURALE — pourquoi ce fichier est dans `scripts/` et pas dans
`src/aegis_trade/`. Il route des ordres réels sans passer par le `RiskEngine`.
CLAUDE.md interdit qu'un chemin de code du système puisse faire ça. Le garder
hors du paquet garantit qu'aucun import depuis `src/` ne peut l'atteindre : c'est
un instrument de mesure, jamais un composant d'exécution. Les garde-fous ci-
dessous (compte démo obligatoire, mise plafonnée, nombre d'allers-retours
plafonné) remplacent le risk check absent, et sont volontairement rigides.

AUTHENTIFICATION — nouvelle API Deriv, pas l'API WebSocket v3 historique. Le
message `authorize` in-band N'EXISTE PLUS (aucun `authorize_request.schema.json`
dans le spec officiel) et un Personal Access Token est rejeté par l'ancien point
d'entrée avec `InvalidToken`. Le jeton ne transite donc plus jamais par le
WebSocket. La séquence est :

    GET  /trading/v1/options/accounts                 (Bearer PAT + Deriv-App-ID)
    POST /trading/v1/options/accounts/{id}/otp        -> data.url
    connexion au WebSocket sur cette URL, l'OTP y est déjà en query

Conséquence pour le garde-fou : `is_virtual` n'existe plus non plus. Le nouveau
modèle porte `account_type: "demo" | "real"`, et Deriv confirme le canal
réellement ouvert dans le chemin de l'URL (`/ws/demo` vs `/ws/real`). Les deux
sont vérifiés — le premier est déclaratif, le second fait foi.

Usage :
    .venv/bin/python scripts/measure_deriv_live_round_trip.py \\
        --symbol CRASH1000 --trades 5 --stake 10 --multiplier 100 --hold 5

`DERIV_API_TOKEN` (PAT, portée `trade`) et `DERIV_APP_ID` sont lus dans `.env`.
Ni le token ni l'OTP ne sont journalisés : l'URL renvoyée par l'OTP porte un
identifiant de connexion dans sa query et est systématiquement caviardée.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Protocol
from urllib.parse import urlsplit

import httpx
import websockets
from dotenv import load_dotenv

logger = logging.getLogger("deriv_live_round_trip")

# Nouvelle API Deriv. L'ancien `wss://ws.derivws.com/websockets/v3?app_id=...`
# n'accepte pas les Personal Access Tokens et n'est donc plus une route.
DERIV_REST_BASE = "https://api.derivws.com"
ACCOUNTS_PATH = "/trading/v1/options/accounts"
REST_TIMEOUT_SECONDS = 30.0

# Deriv encode le type de canal dans le chemin de l'URL renvoyée par l'OTP.
# C'est la seule affirmation de démo qui vienne du serveur et non de nous.
DEMO_WS_PATH_SUFFIX = "/ws/demo"

BPS_PER_UNIT = 10_000.0

# Garde-fous. Ce script contourne le RiskEngine par construction ; ces trois
# plafonds sont le seul frein qui reste, donc ils sont durs, pas configurables
# en ligne de commande. Les relever demande d'éditer le fichier — c'est-à-dire
# de prendre la décision consciemment.
MAX_STAKE_USD = 50.0
MAX_TRADES_PER_RUN = 20
MAX_HOLD_SECONDS = 60.0

CONTRACT_TYPE_BY_DIRECTION = {1: "MULTUP", -1: "MULTDOWN"}

DEFAULT_CSV_PATH = Path("data/measurements/deriv_round_trips.csv")


class DerivApiError(RuntimeError):
    """Erreur renvoyée par l'API Deriv, remontée telle quelle.

    Jamais absorbée : un aller-retour dont l'ouverture a échoué mais dont la
    fermeture est tentée quand même produirait une ligne de CSV cohérente en
    apparence et fausse en valeur.
    """


class DerivRestError(DerivApiError):
    """Échec du préambule REST (liste de comptes, OTP).

    Sous-classe de `DerivApiError` : pour l'appelant, une authentification qui
    échoue et un ordre qui échoue sont le même type d'incident — l'API refuse.
    """


class LiveAccountRefused(RuntimeError):
    """Le compte visé n'est pas un compte démo.

    Le script s'arrête avant tout ordre. Mesurer un coût de transaction ne vaut
    pas le risque d'ouvrir une position financée par erreur.
    """


@dataclass(frozen=True)
class DemoSession:
    """Ce que le préambule REST produit : de quoi ouvrir le WebSocket, et rien de plus."""

    account_id: str
    currency: str
    balance: Optional[float]
    ws_url: str


def redact_otp(url: str) -> str:
    """Retire l'OTP d'une URL avant journalisation.

    L'URL renvoyée par Deriv porte un identifiant de connexion dans sa query.
    La journaliser telle quelle publierait un secret d'authentification dans
    des logs de mesure — qui, eux, n'ont aucune raison d'être protégés.
    """
    base, separator, _query = url.partition("?")
    return f"{base}?otp=***" if separator else base


def _rest_error_text(response: httpx.Response) -> str:
    """Résume l'erreur d'une réponse REST sans jamais renvoyer les en-têtes.

    Deriv répond parfois en texte brut (`Invalid application`) et parfois avec
    un bloc `errors` structuré : les deux doivent rester lisibles.
    """
    try:
        body: Any = response.json()
    except ValueError:
        return response.text.strip()[:200] or "corps vide"

    if isinstance(body, dict):
        errors = body.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            first: dict[str, Any] = errors[0]
            return f"{first.get('code', '?')} : {first.get('message', '?')}"
    return json.dumps(body)[:200]


class DerivRestClient:
    """Préambule d'authentification de la nouvelle API Deriv.

    Le PAT ne sert QUE ici. Il ne descend jamais jusqu'au WebSocket : ce qui y
    descend est un OTP à usage unique, dérivé du compte explicitement choisi.
    """

    def __init__(self, http: httpx.AsyncClient, app_id: str, token: str) -> None:
        self._http = http
        self._headers = {
            "Deriv-App-ID": app_id,
            "Authorization": f"Bearer {token}",
        }

    async def _call(self, method: str, path: str) -> dict[str, Any]:
        response = await self._http.request(
            method, f"{DERIV_REST_BASE}{path}", headers=self._headers
        )
        if response.status_code >= 400:
            raise DerivRestError(
                f"{method} {path} : HTTP {response.status_code} — {_rest_error_text(response)}"
            )
        try:
            body: Any = response.json()
        except ValueError as exc:
            raise DerivRestError(f"{method} {path} : réponse non JSON.") from exc
        if not isinstance(body, dict):
            raise DerivRestError(f"{method} {path} : réponse de forme inattendue.")
        return body

    async def list_accounts(self) -> list[dict[str, Any]]:
        body = await self._call("GET", ACCOUNTS_PATH)
        data = body.get("data")
        if not isinstance(data, list):
            raise DerivRestError("Réponse `/accounts` sans liste `data` exploitable.")
        return [account for account in data if isinstance(account, dict)]

    async def request_otp(self, account_id: str) -> str:
        """Rend l'URL WebSocket prête à l'emploi, OTP déjà en query."""
        body = await self._call("POST", f"{ACCOUNTS_PATH}/{account_id}/otp")
        data = body.get("data")
        url = data.get("url") if isinstance(data, dict) else None
        if not isinstance(url, str) or not url:
            raise DerivRestError(f"Aucune URL WebSocket renvoyée pour le compte {account_id}.")
        return url


def _refuse_unless_demo(account: dict[str, Any]) -> None:
    """Refuse tout compte dont `account_type` n'est pas exactement `demo`.

    Champ absent = refus, comme un type `real`. Un défaut permissif
    transformerait une réponse tronquée en autorisation de trader en réel.
    """
    account_type = account.get("account_type")
    if account_type != "demo":
        raise LiveAccountRefused(
            f"Compte {account.get('account_id', '?')} de type {account_type!r} : "
            "ce script passe des ordres sans risk check et refuse tout compte "
            "qui n'est pas explicitement `demo`."
        )


def select_demo_account(
    accounts: list[dict[str, Any]], requested_account_id: Optional[str] = None
) -> dict[str, Any]:
    """Choisit le compte à trader, et refuse tout ce qui n'est pas démo.

    Le choix est explicite plutôt qu'implicite : sans `--account-id`, un compte
    démo actif et un seul est retenu. Plusieurs candidats sans consigne serait
    un choix arbitraire sur un compte qui passe des ordres — on refuse.
    """
    if requested_account_id is not None:
        matching = [a for a in accounts if a.get("account_id") == requested_account_id]
        if not matching:
            raise DerivRestError(
                f"Compte {requested_account_id} absent de la liste renvoyée par Deriv."
            )
        _refuse_unless_demo(matching[0])
        return matching[0]

    demos = [a for a in accounts if a.get("account_type") == "demo"]
    if not demos:
        seen = sorted({str(a.get("account_type")) for a in accounts})
        raise LiveAccountRefused(
            "Aucun compte `demo` dans la liste renvoyée par Deriv "
            f"(types vus : {seen or ['aucun compte']}). Aucun ordre n'est envoyé."
        )

    active = [a for a in demos if a.get("status") == "active"]
    if not active:
        raise DerivRestError(
            "Comptes démo trouvés mais aucun actif "
            f"(statuts : {sorted({str(a.get('status')) for a in demos})})."
        )
    if len(active) > 1:
        raise DerivRestError(
            f"{len(active)} comptes démo actifs : "
            f"{[str(a.get('account_id')) for a in active]}. "
            "Préciser lequel avec `--account-id` — ce script passe des ordres, "
            "il ne devine pas sur lequel."
        )
    return active[0]


def assert_demo_ws_url(url: str, account_id: str) -> None:
    """Second garde-fou, celui-ci affirmé par le serveur.

    `account_type` est déclaratif et vient d'une liste lue avant l'OTP. Le
    chemin de l'URL renvoyée (`/ws/demo` contre `/ws/real`) est ce que Deriv
    ouvre réellement. Vérifier les deux évite qu'un compte mal apparié ouvre un
    canal réel malgré un garde-fou déclaratif satisfait.
    """
    parts = urlsplit(url)
    if parts.scheme != "wss" or not parts.path.endswith(DEMO_WS_PATH_SUFFIX):
        raise LiveAccountRefused(
            f"URL WebSocket hors canal démo pour {account_id} : {redact_otp(url)}. "
            "Connexion refusée."
        )


def _optional_float(value: object) -> Optional[float]:
    """Le solde n'est que journalisé : son absence ne doit pas arrêter la mesure."""
    if isinstance(value, (int, float)):
        return float(value)
    return None


async def open_demo_session(
    rest: DerivRestClient, requested_account_id: Optional[str] = None
) -> DemoSession:
    accounts = await rest.list_accounts()
    account = select_demo_account(accounts, requested_account_id)
    account_id = str(account["account_id"])

    ws_url = await rest.request_otp(account_id)
    assert_demo_ws_url(ws_url, account_id)

    return DemoSession(
        account_id=account_id,
        currency=str(account.get("currency", "?")),
        balance=_optional_float(account.get("balance")),
        ws_url=ws_url,
    )


class _Connection(Protocol):
    """Ce que le client attend d'une connexion WebSocket.

    Protocole local plutôt que `websockets.WebSocketClientProtocol` : ce dernier
    n'est pas résolvable par mypy en websockets 16.x.
    """

    async def send(self, message: str) -> None: ...

    async def recv(self) -> str | bytes: ...


@dataclass(frozen=True)
class RoundTrip:
    """Un aller-retour complet, tel qu'écrit dans le CSV.

    Tous les champs sont des relevés bruts. Rien n'y est dérivé : les grandeurs
    calculées sont des propriétés, pour qu'une ligne de CSV relue puisse
    toujours être recalculée et vérifiée.
    """

    opened_at: str
    symbol: str
    contract_type: str
    contract_id: int
    stake_usd: float
    multiplier: float
    hold_seconds: float
    requested_entry_spot: float
    entry_spot: float
    requested_exit_spot: float
    exit_spot: float
    realised_pnl_usd: float

    @property
    def direction(self) -> int:
        return 1 if self.contract_type == "MULTUP" else -1

    @property
    def notional_usd(self) -> float:
        """Assiette de la commission : la mise AMPLIFIÉE, pas la mise."""
        return self.stake_usd * self.multiplier

    @property
    def gross_usd(self) -> float:
        """P&L qu'aurait rendu le mouvement de prix seul, sans aucun péage."""
        return (
            self.notional_usd
            * self.direction
            * (self.exit_spot / self.entry_spot - 1.0)
        )

    @property
    def execution_cost_bps(self) -> float:
        """Péage sur les spots RÉELLEMENT exécutés.

        Le terme de prix s'annule exactement, donc le mouvement du marché
        pendant la détention ne contamine pas le résultat. C'est la grandeur
        directement comparable aux 0.745 / 1.063 bps de l'ADR 0021.
        """
        return (self.gross_usd - self.realised_pnl_usd) / self.notional_usd * BPS_PER_UNIT

    @property
    def entry_slippage_bps(self) -> float:
        """Écart entre le spot vu à la décision et le spot obtenu, signé en coût.

        Positif = défavorable. Pour un MULTUP, entrer plus haut que prévu coûte ;
        pour un MULTDOWN, c'est l'inverse — d'où la multiplication par le sens.
        """
        drift = (self.entry_spot - self.requested_entry_spot) / self.requested_entry_spot
        return self.direction * drift * BPS_PER_UNIT

    @property
    def exit_slippage_bps(self) -> float:
        """Idem à la sortie, avec le signe inversé : sortir plus bas coûte au long."""
        drift = (self.requested_exit_spot - self.exit_spot) / self.requested_exit_spot
        return self.direction * drift * BPS_PER_UNIT

    @property
    def slippage_bps(self) -> float:
        return self.entry_slippage_bps + self.exit_slippage_bps

    @property
    def total_cost_bps(self) -> float:
        """Ce qu'une stratégie paie vraiment : péage + slippage.

        C'est ce chiffre, pas `execution_cost_bps`, qui doit alimenter le seuil
        d'entrée d'un modèle. Le distinguer est le seul intérêt de ce script par
        rapport au relevé manuel.
        """
        return self.execution_cost_bps + self.slippage_bps

    def as_csv_row(self) -> dict[str, object]:
        row: dict[str, object] = dict(asdict(self))
        row.update(
            {
                "notional_usd": round(self.notional_usd, 2),
                "gross_usd": round(self.gross_usd, 6),
                "execution_cost_bps": round(self.execution_cost_bps, 4),
                "entry_slippage_bps": round(self.entry_slippage_bps, 4),
                "exit_slippage_bps": round(self.exit_slippage_bps, 4),
                "slippage_bps": round(self.slippage_bps, 4),
                "total_cost_bps": round(self.total_cost_bps, 4),
            }
        )
        return row


CSV_COLUMNS = [
    "opened_at",
    "symbol",
    "contract_type",
    "contract_id",
    "stake_usd",
    "multiplier",
    "notional_usd",
    "hold_seconds",
    "requested_entry_spot",
    "entry_spot",
    "requested_exit_spot",
    "exit_spot",
    "realised_pnl_usd",
    "gross_usd",
    "execution_cost_bps",
    "entry_slippage_bps",
    "exit_slippage_bps",
    "slippage_bps",
    "total_cost_bps",
]


def append_round_trips(path: Path, round_trips: list[RoundTrip]) -> None:
    """Ajoute les relevés au CSV, en écrivant l'en-tête si le fichier est neuf.

    Append et non écrasement : chaque session est une mesure indépendante, et
    l'accumulation est ce qui permettra un jour de dire si le coût dérive.
    """
    if not round_trips:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        if is_new:
            writer.writeheader()
        for round_trip in round_trips:
            writer.writerow(round_trip.as_csv_row())


class DerivTradingClient:
    """Client Deriv minimal : authentifier, acheter, vendre, relire un contrat.

    Une seule connexion pour toute la session : rouvrir un WebSocket par ordre
    ajouterait la latence de handshake au slippage mesuré, ce qui reviendrait à
    mesurer la qualité du réseau et à l'appeler coût de marché.
    """

    def __init__(self, connection: _Connection) -> None:
        self._connection = connection
        self._req_id = 0

    async def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envoie une requête et rend LA réponse correspondante.

        L'appariement par `req_id` n'est pas décoratif : Deriv intercale des
        messages non sollicités (`ping`, accusés). Lire « le prochain message »
        attribuerait la réponse d'un ordre à un autre, donc un spot d'entrée à
        un mauvais contrat.
        """
        self._req_id += 1
        req_id = self._req_id
        await self._connection.send(json.dumps({**payload, "req_id": req_id}))

        while True:
            raw = await self._connection.recv()
            text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            message: Any = json.loads(text)
            if not isinstance(message, dict):
                continue
            if message.get("req_id") != req_id:
                continue
            error = message.get("error")
            if isinstance(error, dict):
                raise DerivApiError(
                    f"{error.get('code', 'UnknownError')} : {error.get('message', text[:200])}"
                )
            return message

    async def latest_spot(self, symbol: str) -> float:
        """Dernier prix connu, relevé juste avant l'ordre.

        Requête ponctuelle plutôt qu'abonnement : un flux de ticks arriverait de
        façon asynchrone et il faudrait décider quel tick était « celui de la
        décision ». Ici la réponse EST le prix au moment de la décision.
        """
        response = await self._request(
            {"ticks_history": symbol, "count": 1, "end": "latest", "style": "ticks"}
        )
        history = response.get("history")
        if not isinstance(history, dict):
            raise DerivApiError(f"Réponse `ticks_history` sans historique pour {symbol}.")
        prices = history.get("prices")
        if not isinstance(prices, list) or not prices:
            raise DerivApiError(f"Aucun prix renvoyé pour {symbol}.")
        return float(prices[-1])

    async def buy_multiplier(
        self, symbol: str, direction: int, stake_usd: float, multiplier: float
    ) -> dict[str, Any]:
        contract_type = CONTRACT_TYPE_BY_DIRECTION[direction]
        response = await self._request(
            {
                "buy": "1",
                # `price` est le prix MAXIMUM accepté. L'égaler à la mise est ce
                # qui rend l'ordre non-slippable en coût d'achat : le contrat est
                # refusé plutôt que rempli plus cher.
                "price": stake_usd,
                "parameters": {
                    "amount": stake_usd,
                    "basis": "stake",
                    "contract_type": contract_type,
                    "currency": "USD",
                    "multiplier": multiplier,
                    # La nouvelle API nomme ce champ `underlying_symbol`.
                    # `symbol` est accepté à la sérialisation puis rejeté côté
                    # serveur : rupture silencieuse, pas erreur de typage.
                    "underlying_symbol": symbol,
                },
            }
        )
        contract = response.get("buy")
        if not isinstance(contract, dict) or "contract_id" not in contract:
            raise DerivApiError(f"Achat {contract_type} {symbol} sans `contract_id`.")
        return contract

    async def open_contract(self, contract_id: int) -> dict[str, Any]:
        response = await self._request(
            {"proposal_open_contract": 1, "contract_id": contract_id}
        )
        contract = response.get("proposal_open_contract")
        if not isinstance(contract, dict):
            raise DerivApiError(f"Contrat {contract_id} illisible.")
        return contract

    async def sell(self, contract_id: int) -> dict[str, Any]:
        # `price: 0` = vendre au marché. Un prix plancher ferait échouer la
        # vente sur un mouvement défavorable, laissant une position ouverte —
        # exactement ce qu'un script sans surveillance ne doit jamais produire.
        response = await self._request({"sell": contract_id, "price": 0})
        sold = response.get("sell")
        if not isinstance(sold, dict):
            raise DerivApiError(f"Vente du contrat {contract_id} sans confirmation.")
        return sold


def _require_float(contract: dict[str, Any], field: str, contract_id: int) -> float:
    value = contract.get(field)
    if not isinstance(value, (int, float, str)):
        raise DerivApiError(
            f"Contrat {contract_id} : `{field}` absent ou illisible ({value!r}). "
            "Aucune valeur par défaut n'est substituée — un spot inventé "
            "produirait un coût faux et crédible."
        )
    return float(value)


async def run_round_trip(
    client: DerivTradingClient,
    symbol: str,
    direction: int,
    stake_usd: float,
    multiplier: float,
    hold_seconds: float,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> RoundTrip:
    """Un aller-retour complet, du spot de décision au P&L réalisé.

    `sleep` est injectable pour que les tests n'attendent pas réellement : la
    durée de détention n'a aucune incidence sur l'arithmétique du coût, seule
    la séquence d'appels compte.
    """
    requested_entry_spot = await client.latest_spot(symbol)
    opened_at = datetime.now(timezone.utc).isoformat()
    bought = await client.buy_multiplier(symbol, direction, stake_usd, multiplier)
    contract_id = int(bought["contract_id"])

    try:
        await sleep(hold_seconds)
        requested_exit_spot = await client.latest_spot(symbol)
        await client.sell(contract_id)
    except BaseException:
        # Une exception entre l'achat et la vente laisserait une position
        # ouverte sur le compte. On tente la fermeture avant de propager ;
        # l'échec de secours est journalisé, jamais substitué à l'erreur
        # d'origine qui, elle, est la vraie cause.
        try:
            await client.sell(contract_id)
        except Exception:
            logger.exception(
                "Contrat %s NON FERMÉ après échec. Le fermer manuellement.", contract_id
            )
        raise

    settled = await client.open_contract(contract_id)
    return RoundTrip(
        opened_at=opened_at,
        symbol=symbol,
        contract_type=CONTRACT_TYPE_BY_DIRECTION[direction],
        contract_id=contract_id,
        stake_usd=stake_usd,
        multiplier=multiplier,
        hold_seconds=hold_seconds,
        requested_entry_spot=requested_entry_spot,
        entry_spot=_require_float(settled, "entry_spot", contract_id),
        requested_exit_spot=requested_exit_spot,
        exit_spot=_require_float(settled, "exit_spot", contract_id),
        realised_pnl_usd=_require_float(settled, "profit", contract_id),
    )


def validate_run_parameters(stake_usd: float, trades: int, hold_seconds: float) -> None:
    """Applique les plafonds durs avant toute connexion.

    Échouer ici coûte zéro ordre. Échouer après la première ouverture en
    laisserait une série derrière soi.
    """
    if not 0.0 < stake_usd <= MAX_STAKE_USD:
        raise ValueError(
            f"Mise {stake_usd} USD hors bornes : attendu 0 < mise <= {MAX_STAKE_USD}."
        )
    if not 0 < trades <= MAX_TRADES_PER_RUN:
        raise ValueError(
            f"{trades} allers-retours demandés : attendu 0 < n <= {MAX_TRADES_PER_RUN}."
        )
    if not 0.0 <= hold_seconds <= MAX_HOLD_SECONDS:
        raise ValueError(
            f"Détention {hold_seconds}s hors bornes : attendu 0 <= t <= {MAX_HOLD_SECONDS}."
        )


def summarise(round_trips: list[RoundTrip]) -> None:
    """Résumé lisible. La médiane, pas la moyenne : sur cinq mesures, une seule
    saisie retardée déplacerait une moyenne bien plus qu'une médiane."""
    if not round_trips:
        print("\n  Aucun aller-retour abouti.\n")
        return

    from statistics import median

    symbol = round_trips[0].symbol
    execution = [rt.execution_cost_bps for rt in round_trips]
    slippage = [rt.slippage_bps for rt in round_trips]
    total = [rt.total_cost_bps for rt in round_trips]

    print("\n" + "=" * 72)
    print(f"  {symbol} — {len(round_trips)} allers-retours, compte démo")
    print("=" * 72)
    print(f"    coûts d'exécution (bps)  : {'  '.join(f'{c:.3f}' for c in sorted(execution))}")
    print(f"    slippage (bps)           : {'  '.join(f'{s:+.3f}' for s in sorted(slippage))}")
    print(f"    MÉDIANE exécution        : {median(execution):.3f} bps")
    print(f"    MÉDIANE slippage         : {median(slippage):+.3f} bps")
    print(f"    MÉDIANE coût tout compris: {median(total):.3f} bps")
    print("\n  Comparer la médiane d'exécution aux 0.745 (Crash) / 1.063 (Boom) bps")
    print("  de l'ADR 0021 : c'est la même grandeur. Le slippage est en plus, et")
    print("  c'est le coût tout compris qui doit alimenter un seuil d'entrée.")
    print("=" * 72 + "\n")


async def run_session(
    token: str,
    app_id: str,
    symbol: str,
    direction: int,
    stake_usd: float,
    multiplier: float,
    trades: int,
    hold_seconds: float,
    csv_path: Path,
    account_id: Optional[str] = None,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> list[RoundTrip]:
    """Préambule REST, puis toute la session de mesure sur une seule connexion.

    `transport` est injectable pour que les tests couvrent le préambule sans
    réseau. Il ne sert à rien d'autre : en production il vaut `None` et httpx
    ouvre son transport par défaut.
    """
    round_trips: list[RoundTrip] = []

    async with httpx.AsyncClient(
        timeout=REST_TIMEOUT_SECONDS, transport=transport
    ) as http:
        session = await open_demo_session(
            DerivRestClient(http, app_id, token), account_id
        )

    logger.info(
        "Compte démo %s (devise %s, solde %s) — WebSocket %s.",
        session.account_id,
        session.currency,
        session.balance,
        redact_otp(session.ws_url),
    )

    async with websockets.connect(session.ws_url) as connection:
        client = DerivTradingClient(connection)

        for index in range(trades):
            try:
                round_trip = await run_round_trip(
                    client, symbol, direction, stake_usd, multiplier, hold_seconds
                )
            except DerivApiError:
                # Un aller-retour raté n'invalide pas les précédents. On
                # journalise, on écrit ce qui est acquis, et on s'arrête : une
                # API qui refuse un ordre refusera probablement le suivant.
                logger.exception("Aller-retour %d/%d échoué, arrêt.", index + 1, trades)
                break
            round_trips.append(round_trip)
            logger.info(
                "A/R %d/%d : exécution %.3f bps, slippage %+.3f bps.",
                index + 1,
                trades,
                round_trip.execution_cost_bps,
                round_trip.slippage_bps,
            )

    append_round_trips(csv_path, round_trips)
    return round_trips


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", maxsplit=1)[0])
    parser.add_argument("--symbol", default="CRASH1000")
    parser.add_argument(
        "--direction",
        type=int,
        choices=(1, -1),
        default=1,
        help="1 = MULTUP, -1 = MULTDOWN.",
    )
    parser.add_argument("--stake", type=float, default=10.0, help="Mise en USD.")
    parser.add_argument("--multiplier", type=float, default=100.0)
    parser.add_argument("--trades", type=int, default=5)
    parser.add_argument("--hold", type=float, default=5.0, help="Détention en secondes.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument(
        "--account-id",
        default=None,
        help="Compte à trader. Obligatoire si le PAT en expose plusieurs actifs.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)

    try:
        validate_run_parameters(args.stake, args.trades, args.hold)
    except ValueError as exc:
        logger.error("%s", exc)
        return 2

    load_dotenv()
    token = os.environ.get("DERIV_API_TOKEN", "").strip()
    if not token:
        logger.error("`DERIV_API_TOKEN` absent de l'environnement et de `.env`.")
        return 2

    app_id = os.environ.get("DERIV_APP_ID", "").strip()
    if not app_id:
        logger.error(
            "`DERIV_APP_ID` absent de l'environnement et de `.env`. La nouvelle "
            "API Deriv rejette tout Personal Access Token sans en-tête "
            "`Deriv-App-ID` : enregistrer une application sur "
            "https://home.deriv.com/dashboard puis renseigner son identifiant."
        )
        return 2

    try:
        round_trips = asyncio.run(
            run_session(
                token=token,
                app_id=app_id,
                symbol=args.symbol,
                direction=args.direction,
                stake_usd=args.stake,
                multiplier=args.multiplier,
                trades=args.trades,
                hold_seconds=args.hold,
                csv_path=args.csv,
                account_id=args.account_id,
            )
        )
    except LiveAccountRefused as exc:
        logger.error("%s", exc)
        return 3
    except DerivApiError as exc:
        logger.error("API Deriv : %s", exc)
        return 4

    summarise(round_trips)
    if round_trips:
        logger.info("%d lignes ajoutées à %s.", len(round_trips), args.csv)
    return 0 if round_trips else 1


if __name__ == "__main__":
    raise SystemExit(main())
