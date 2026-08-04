"""Client d'aller-retours Multipliers Deriv : garde-fous, appariement, coûts.

Ce script route des ordres sans passer par le `RiskEngine` — c'est la raison
pour laquelle il vit dans `scripts/`. Les tests ci-dessous couvrent donc en
priorité ce qui remplace le risk check absent : refus d'un compte réel, plafonds
de mise et de volume, fermeture garantie d'une position ouverte.

Aucun réseau, sur les DEUX couches de la nouvelle API : le préambule REST passe
par un `httpx.MockTransport`, et le WebSocket par une connexion doublée qui
répond à partir du contenu de la requête, `req_id` compris. Le protocole n'est
raccourci sur aucune des deux.
"""

from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path
from typing import Any, Optional

import httpx
import pytest

from scripts.measure_deriv_live_round_trip import (
    MAX_HOLD_SECONDS,
    MAX_STAKE_USD,
    MAX_TRADES_PER_RUN,
    DerivApiError,
    DerivRestClient,
    DerivRestError,
    DerivTradingClient,
    LiveAccountRefused,
    RoundTrip,
    append_round_trips,
    assert_demo_ws_url,
    main,
    open_demo_session,
    redact_otp,
    run_round_trip,
    run_session,
    select_demo_account,
    summarise,
    validate_run_parameters,
)

SYMBOL = "CRASH1000"
CONTRACT_ID = 987654321

APP_ID = "99999"
TOKEN = "pat-secret-value"
OTP = "one-time-secret"
DEMO_WS_URL = f"wss://api.derivws.com/trading/v1/options/ws/demo?otp={OTP}"
REAL_WS_URL = f"wss://api.derivws.com/trading/v1/options/ws/real?otp={OTP}"

DEMO_ACCOUNT: dict[str, Any] = {
    "account_id": "VRTC1234",
    "account_type": "demo",
    "currency": "USD",
    "balance": 10_000.0,
    "status": "active",
}
REAL_ACCOUNT: dict[str, Any] = {
    "account_id": "CR1234",
    "account_type": "real",
    "currency": "USD",
    "balance": 42.0,
    "status": "active",
}


def _response(status: int, body: object) -> httpx.Response:
    if isinstance(body, str):
        return httpx.Response(status, text=body)
    return httpx.Response(status, json=body)


class _FakeRestApi:
    """Préambule REST doublé : liste de comptes puis OTP.

    Les deux points d'entrée sont paramétrables indépendamment parce que leurs
    modes de défaillance ne sont pas les mêmes : le premier peut mentir sur le
    type de compte, le second sur le canal réellement ouvert.
    """

    def __init__(
        self,
        *,
        accounts: Optional[list[dict[str, Any]]] = None,
        accounts_status: int = 200,
        accounts_body: object = None,
        otp_url: str = DEMO_WS_URL,
        otp_status: int = 200,
        otp_body: object = None,
    ) -> None:
        self._accounts_status = accounts_status
        self._accounts_body: object = (
            accounts_body
            if accounts_body is not None
            else {"data": accounts if accounts is not None else [DEMO_ACCOUNT]}
        )
        self._otp_status = otp_status
        self._otp_body: object = (
            otp_body if otp_body is not None else {"data": {"url": otp_url}}
        )
        self.requests: list[httpx.Request] = []

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path.endswith("/otp"):
            return _response(self._otp_status, self._otp_body)
        return _response(self._accounts_status, self._accounts_body)


def _call_rest(api: _FakeRestApi, method: str, *args: object) -> Any:
    async def _run() -> Any:
        async with httpx.AsyncClient(transport=api.transport) as http:
            client = DerivRestClient(http, APP_ID, TOKEN)
            return await getattr(client, method)(*args)

    return asyncio.run(_run())


def _open_session(api: _FakeRestApi, account_id: Optional[str] = None) -> Any:
    async def _run() -> Any:
        async with httpx.AsyncClient(transport=api.transport) as http:
            return await open_demo_session(DerivRestClient(http, APP_ID, TOKEN), account_id)

    return asyncio.run(_run())


class _FakeDerivServer:
    """Connexion doublée qui répond en fonction de la requête reçue.

    Répondre au contenu et non à un ordre d'appel figé : c'est ce qui permet
    d'exercer l'appariement par `req_id` et les erreurs ciblées sans réécrire
    une file de messages à chaque test.

    Aucune réponse `authorize` : ce message n'existe plus dans la nouvelle API,
    le jeton ne transite jamais par le WebSocket.
    """

    def __init__(
        self,
        *,
        spots: list[float] | None = None,
        entry_spot: float = 5800.0,
        exit_spot: float = 5800.0,
        profit: float = -0.06,
        settled_extra: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
        noise_before_reply: int = 0,
    ) -> None:
        self.spots = list(spots or [5800.0, 5800.0])
        self.entry_spot = entry_spot
        self.exit_spot = exit_spot
        self.profit = profit
        self.settled_extra = settled_extra or {}
        self.errors = errors or {}
        self.noise_before_reply = noise_before_reply
        self.requests: list[dict[str, Any]] = []
        self._outbound: list[str] = []

    async def send(self, message: str) -> None:
        payload = json.loads(message)
        self.requests.append(payload)
        # Bruit non sollicité (pings Deriv) : le client doit le sauter, pas
        # l'attribuer à la requête en cours.
        for _ in range(self.noise_before_reply):
            self._outbound.append(json.dumps({"msg_type": "ping", "ping": "pong"}))
        self._outbound.append(json.dumps(self._reply(payload)))

    async def recv(self) -> str:
        if not self._outbound:
            raise ConnectionError("flux terminé")
        return self._outbound.pop(0)

    async def __aenter__(self) -> "_FakeDerivServer":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def _reply(self, payload: dict[str, Any]) -> dict[str, Any]:
        req_id = payload["req_id"]
        for key, message in self.errors.items():
            if key in payload:
                return {"req_id": req_id, "error": {"code": "TestError", "message": message}}

        if "ticks_history" in payload:
            spot = self.spots.pop(0) if self.spots else 5800.0
            return {"req_id": req_id, "history": {"prices": [spot], "times": [1_770_000_000]}}
        if "buy" in payload:
            return {
                "req_id": req_id,
                "buy": {"contract_id": CONTRACT_ID, "buy_price": payload["price"]},
            }
        if "sell" in payload:
            return {"req_id": req_id, "sell": {"contract_id": CONTRACT_ID, "sold_for": 9.94}}
        if "proposal_open_contract" in payload:
            contract: dict[str, Any] = {
                "contract_id": CONTRACT_ID,
                "entry_spot": self.entry_spot,
                "exit_spot": self.exit_spot,
                "profit": self.profit,
                "is_sold": 1,
            }
            contract.update(self.settled_extra)
            return {"req_id": req_id, "proposal_open_contract": contract}
        raise AssertionError(f"Requête non gérée par le double : {payload}")


async def _noop_sleep(_seconds: float) -> None:
    """Détention instantanée : la durée n'entre dans aucun calcul de coût."""
    return None


def _round_trip(server: _FakeDerivServer, direction: int = 1) -> RoundTrip:
    return asyncio.run(
        run_round_trip(
            DerivTradingClient(server),
            symbol=SYMBOL,
            direction=direction,
            stake_usd=10.0,
            multiplier=100.0,
            hold_seconds=5.0,
            sleep=_noop_sleep,
        )
    )


class TestRestPreamble:
    """Le PAT ne sert qu'ici. Ce qui descend au WebSocket est un OTP dérivé."""

    def test_every_call_carries_the_pat_and_the_app_id(self) -> None:
        """Sans `Deriv-App-ID`, la nouvelle API rejette tout PAT — l'en-tête
        n'est pas optionnel, c'est la moitié de l'authentification."""
        api = _FakeRestApi()

        _call_rest(api, "list_accounts")

        request = api.requests[0]
        assert request.headers["Deriv-App-ID"] == APP_ID
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"

    def test_otp_is_requested_on_the_chosen_account(self) -> None:
        api = _FakeRestApi()

        url = _call_rest(api, "request_otp", "VRTC1234")

        assert url == DEMO_WS_URL
        assert api.requests[0].method == "POST"
        assert api.requests[0].url.path.endswith("/accounts/VRTC1234/otp")

    def test_structured_error_block_is_reported(self) -> None:
        api = _FakeRestApi(
            accounts_status=401,
            accounts_body={"errors": [{"code": "Unauthorized", "message": "bad token"}]},
        )

        with pytest.raises(DerivRestError, match="Unauthorized"):
            _call_rest(api, "list_accounts")

    def test_plain_text_error_is_reported(self) -> None:
        """Deriv répond `Invalid application` en texte brut sur un app id
        inconnu. Un parseur qui n'accepterait que du JSON masquerait la seule
        information utile du refus."""
        api = _FakeRestApi(accounts_status=400, accounts_body="Invalid application")

        with pytest.raises(DerivRestError, match="Invalid application"):
            _call_rest(api, "list_accounts")

    def test_json_error_without_an_errors_block_is_reported_verbatim(self) -> None:
        """Corps JSON de forme inconnue : le rendre tel quel est la seule
        option honnête. Le résumer sur une clé devinée masquerait le refus."""
        api = _FakeRestApi(
            accounts_status=403, accounts_body={"detail": "app id not registered"}
        )

        with pytest.raises(DerivRestError, match="app id not registered"):
            _call_rest(api, "list_accounts")

    def test_empty_error_body_still_names_the_call(self) -> None:
        api = _FakeRestApi(accounts_status=500, accounts_body="")

        with pytest.raises(DerivRestError, match="corps vide"):
            _call_rest(api, "list_accounts")

    def test_non_json_success_raises(self) -> None:
        api = _FakeRestApi(accounts_body="pas du JSON")

        with pytest.raises(DerivRestError, match="non JSON"):
            _call_rest(api, "list_accounts")

    def test_non_object_json_raises(self) -> None:
        api = _FakeRestApi(accounts_body=["liste", "au", "lieu", "d'objet"])

        with pytest.raises(DerivRestError, match="forme inattendue"):
            _call_rest(api, "list_accounts")

    def test_response_without_data_list_raises(self) -> None:
        api = _FakeRestApi(accounts_body={"meta": {}})

        with pytest.raises(DerivRestError, match="data"):
            _call_rest(api, "list_accounts")

    def test_non_dict_entries_are_dropped(self) -> None:
        api = _FakeRestApi(accounts_body={"data": [DEMO_ACCOUNT, "bruit", None]})

        assert _call_rest(api, "list_accounts") == [DEMO_ACCOUNT]

    def test_otp_without_url_raises(self) -> None:
        api = _FakeRestApi(otp_body={"data": {}})

        with pytest.raises(DerivRestError, match="Aucune URL"):
            _call_rest(api, "request_otp", "VRTC1234")

    def test_otp_with_empty_url_raises(self) -> None:
        api = _FakeRestApi(otp_body={"data": {"url": ""}})

        with pytest.raises(DerivRestError, match="Aucune URL"):
            _call_rest(api, "request_otp", "VRTC1234")


class TestDemoAccountGuard:
    """Le refus doit intervenir AVANT l'OTP, donc avant toute connexion.

    Ce script contourne le `RiskEngine` par construction : un ordre passé sur un
    compte financé n'aurait aucun garde-fou en aval.
    """

    def test_real_account_is_refused(self) -> None:
        with pytest.raises(LiveAccountRefused, match="demo"):
            select_demo_account([REAL_ACCOUNT], "CR1234")

    def test_missing_account_type_is_refused(self) -> None:
        """Champ absent = non démo. Un défaut permissif transformerait une
        réponse tronquée en autorisation de trader en réel."""
        with pytest.raises(LiveAccountRefused):
            select_demo_account([{"account_id": "X1", "status": "active"}], "X1")

    def test_no_demo_account_at_all_is_refused(self) -> None:
        with pytest.raises(LiveAccountRefused, match="Aucun compte"):
            select_demo_account([REAL_ACCOUNT])

    def test_an_empty_account_list_is_refused(self) -> None:
        with pytest.raises(LiveAccountRefused):
            select_demo_account([])

    def test_requested_account_must_be_in_the_list(self) -> None:
        with pytest.raises(DerivRestError, match="absent"):
            select_demo_account([DEMO_ACCOUNT], "INCONNU")

    def test_a_single_active_demo_account_is_selected(self) -> None:
        assert select_demo_account([REAL_ACCOUNT, DEMO_ACCOUNT]) == DEMO_ACCOUNT

    def test_demo_account_that_is_not_active_is_refused(self) -> None:
        dormant = {**DEMO_ACCOUNT, "status": "disabled"}

        with pytest.raises(DerivRestError, match="aucun actif"):
            select_demo_account([dormant])

    def test_several_active_demo_accounts_demand_an_explicit_choice(self) -> None:
        """Deux candidats sans consigne serait un choix arbitraire sur un compte
        qui passe des ordres. On refuse plutôt que de deviner."""
        second = {**DEMO_ACCOUNT, "account_id": "VRTC5678"}

        with pytest.raises(DerivRestError, match="--account-id"):
            select_demo_account([DEMO_ACCOUNT, second])

    def test_explicit_choice_resolves_the_ambiguity(self) -> None:
        second = {**DEMO_ACCOUNT, "account_id": "VRTC5678"}

        assert select_demo_account([DEMO_ACCOUNT, second], "VRTC5678") == second

    def test_a_real_ws_url_is_refused_even_when_the_account_declared_demo(self) -> None:
        """`account_type` est déclaratif et lu AVANT l'OTP. Le chemin de l'URL
        est ce que Deriv ouvre réellement — c'est lui qui fait foi."""
        with pytest.raises(LiveAccountRefused, match="hors canal démo"):
            assert_demo_ws_url(REAL_WS_URL, "VRTC1234")

    def test_a_non_wss_url_is_refused(self) -> None:
        with pytest.raises(LiveAccountRefused):
            assert_demo_ws_url("https://api.derivws.com/trading/v1/options/ws/demo", "VRTC1234")

    def test_a_demo_url_passes(self) -> None:
        assert_demo_ws_url(DEMO_WS_URL, "VRTC1234")

    def test_a_real_ws_url_aborts_before_any_websocket_is_opened(self) -> None:
        api = _FakeRestApi(otp_url=REAL_WS_URL)

        with pytest.raises(LiveAccountRefused):
            _open_session(api)

    def test_open_demo_session_carries_what_the_websocket_needs(self) -> None:
        session = _open_session(_FakeRestApi())

        assert session.account_id == "VRTC1234"
        assert session.currency == "USD"
        assert session.balance == 10_000.0
        assert session.ws_url == DEMO_WS_URL

    def test_a_missing_balance_does_not_stop_the_measurement(self) -> None:
        """Le solde n'est que journalisé : il n'entre dans aucun calcul de coût."""
        account = {k: v for k, v in DEMO_ACCOUNT.items() if k != "balance"}

        session = _open_session(_FakeRestApi(accounts=[account]))

        assert session.balance is None


class TestOtpRedaction:
    """L'URL renvoyée porte un secret d'authentification dans sa query.

    La journaliser telle quelle publierait ce secret dans des logs de mesure —
    qui, eux, n'ont aucune raison d'être protégés.
    """

    def test_the_otp_is_removed_from_a_redacted_url(self) -> None:
        redacted = redact_otp(DEMO_WS_URL)

        assert OTP not in redacted
        assert redacted.endswith("/ws/demo?otp=***")

    def test_a_url_without_query_is_left_intact(self) -> None:
        url = "wss://api.derivws.com/trading/v1/options/ws/demo"

        assert redact_otp(url) == url

    def test_a_refused_url_is_reported_redacted(self) -> None:
        with pytest.raises(LiveAccountRefused) as excinfo:
            assert_demo_ws_url(REAL_WS_URL, "VRTC1234")

        assert OTP not in str(excinfo.value)

    def test_the_session_log_never_carries_the_raw_otp(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level("INFO")
        _patch_connect(monkeypatch, _FakeDerivServer(spots=[5800.0] * 10))

        asyncio.run(
            run_session(
                token=TOKEN,
                app_id=APP_ID,
                symbol=SYMBOL,
                direction=1,
                stake_usd=10.0,
                multiplier=100.0,
                trades=1,
                hold_seconds=0.0,
                csv_path=tmp_path / "out.csv",
                transport=_FakeRestApi().transport,
            )
        )

        assert OTP not in caplog.text
        assert TOKEN not in caplog.text
        assert "otp=***" in caplog.text


class TestRunParameters:
    @pytest.mark.parametrize(
        "stake,trades,hold",
        [
            (0.0, 5, 5.0),
            (-10.0, 5, 5.0),
            (MAX_STAKE_USD + 0.01, 5, 5.0),
            (10.0, 0, 5.0),
            (10.0, MAX_TRADES_PER_RUN + 1, 5.0),
            (10.0, 5, -1.0),
            (10.0, 5, MAX_HOLD_SECONDS + 1.0),
        ],
    )
    def test_out_of_bounds_parameters_are_refused(
        self, stake: float, trades: int, hold: float
    ) -> None:
        """Les plafonds sont vérifiés AVANT toute connexion : échouer ici ne
        laisse aucune position derrière soi, échouer après le premier achat si."""
        with pytest.raises(ValueError):
            validate_run_parameters(stake, trades, hold)

    def test_nominal_parameters_pass(self) -> None:
        validate_run_parameters(MAX_STAKE_USD, MAX_TRADES_PER_RUN, MAX_HOLD_SECONDS)


class TestProtocol:
    def test_unsolicited_messages_are_skipped(self) -> None:
        """Deriv intercale des messages non sollicités. Lire « le prochain
        message » attribuerait un spot d'entrée au mauvais contrat."""
        server = _FakeDerivServer(noise_before_reply=3)

        spot = asyncio.run(DerivTradingClient(server).latest_spot(SYMBOL))

        assert spot == 5800.0

    def test_every_request_carries_a_distinct_req_id(self) -> None:
        server = _FakeDerivServer(spots=[5800.0, 5801.0])
        _round_trip(server)

        req_ids = [request["req_id"] for request in server.requests]
        assert len(req_ids) == len(set(req_ids))

    def test_no_request_ever_carries_the_token(self) -> None:
        """Le message `authorize` n'existe plus. Si un jeton repassait par le
        WebSocket, ce serait une régression vers l'ancienne API."""
        server = _FakeDerivServer()
        _round_trip(server)

        assert all("authorize" not in request for request in server.requests)

    def test_api_error_is_raised_not_swallowed(self) -> None:
        """Un achat refusé dont l'erreur serait absorbée produirait une ligne de
        CSV cohérente en forme et fausse en valeur."""
        server = _FakeDerivServer(errors={"buy": "InsufficientBalance"})

        with pytest.raises(DerivApiError, match="InsufficientBalance"):
            _round_trip(server)

    def test_buy_caps_the_price_at_the_stake(self) -> None:
        """`price` est le prix maximum accepté : l'égaler à la mise fait refuser
        le contrat plutôt que le remplir plus cher."""
        server = _FakeDerivServer()
        _round_trip(server)

        buy = next(request for request in server.requests if "buy" in request)
        assert buy["price"] == 10.0
        assert buy["parameters"]["contract_type"] == "MULTUP"
        assert buy["parameters"]["multiplier"] == 100.0

    def test_buy_names_the_instrument_underlying_symbol(self) -> None:
        """La nouvelle API attend `underlying_symbol`. L'ancien `symbol` se
        sérialise sans erreur et se fait refuser côté serveur : rupture
        silencieuse, donc épinglée ici."""
        server = _FakeDerivServer()
        _round_trip(server)

        buy = next(request for request in server.requests if "buy" in request)
        assert buy["parameters"]["underlying_symbol"] == SYMBOL
        assert "symbol" not in buy["parameters"]

    def test_direction_minus_one_buys_multdown(self) -> None:
        server = _FakeDerivServer()
        _round_trip(server, direction=-1)

        buy = next(request for request in server.requests if "buy" in request)
        assert buy["parameters"]["contract_type"] == "MULTDOWN"

    def test_missing_entry_spot_raises_instead_of_defaulting(self) -> None:
        """Un spot absent remplacé par une valeur par défaut produirait un coût
        faux et parfaitement crédible — le pire des deux mondes."""
        server = _FakeDerivServer(settled_extra={"entry_spot": None})

        with pytest.raises(DerivApiError, match="entry_spot"):
            _round_trip(server)


class TestPositionIsNeverLeftOpen:
    def test_failure_between_buy_and_sell_still_attempts_a_sell(self) -> None:
        """Une exception après l'achat laisserait sinon une position ouverte sur
        le compte, sans surveillance."""
        server = _FakeDerivServer()

        async def _exploding_sleep(_seconds: float) -> None:
            raise asyncio.CancelledError("interruption pendant la détention")

        with pytest.raises(asyncio.CancelledError):
            asyncio.run(
                run_round_trip(
                    DerivTradingClient(server),
                    symbol=SYMBOL,
                    direction=1,
                    stake_usd=10.0,
                    multiplier=100.0,
                    hold_seconds=5.0,
                    sleep=_exploding_sleep,
                )
            )

        sells = [request for request in server.requests if "sell" in request]
        assert len(sells) == 1
        assert sells[0]["sell"] == CONTRACT_ID

    def test_a_failed_rescue_sell_does_not_mask_the_original_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Si la fermeture de secours échoue elle aussi, l'erreur d'origine
        reste celle qui remonte : c'est elle la cause. Le contrat resté ouvert
        est journalisé en clair, seul moyen pour l'opérateur de le retrouver."""
        server = _FakeDerivServer(errors={"sell": "MarketIsClosed"})

        async def _exploding_sleep(_seconds: float) -> None:
            raise TimeoutError("détention interrompue")

        with pytest.raises(TimeoutError, match="détention interrompue"):
            asyncio.run(
                run_round_trip(
                    DerivTradingClient(server),
                    symbol=SYMBOL,
                    direction=1,
                    stake_usd=10.0,
                    multiplier=100.0,
                    hold_seconds=5.0,
                    sleep=_exploding_sleep,
                )
            )

        assert str(CONTRACT_ID) in caplog.text
        assert "NON FERMÉ" in caplog.text


class TestCostArithmetic:
    def test_execution_cost_matches_the_manual_formula(self) -> None:
        """Même arithmétique que le relevé manuel de l'ADR 0021, sinon les deux
        chiffres ne seraient pas comparables et la mesure automatisée ne
        vérifierait rien.

        Reprise du premier aller-retour Crash 1000 relevé à la main :
        entrée 5813.068, sortie 5813.101, P&L -0.06 USD sur 1000 USD notionnel.
        """
        server = _FakeDerivServer(
            spots=[5813.068, 5813.101], entry_spot=5813.068, exit_spot=5813.101, profit=-0.06
        )

        round_trip = _round_trip(server)

        gross = 1000.0 * (5813.101 / 5813.068 - 1.0)
        assert round_trip.execution_cost_bps == pytest.approx((gross + 0.06) / 1000.0 * 10_000.0)
        assert round_trip.execution_cost_bps == pytest.approx(0.6568, abs=1e-3)

    def test_price_movement_does_not_contaminate_the_cost(self) -> None:
        """Le terme de prix s'annule : deux allers-retours au même péage mais à
        des mouvements de marché opposés doivent rendre le même coût. Sans
        cette propriété, la mesure dépendrait de l'instant du relevé."""
        notional = 1000.0
        toll_usd = 0.0745

        up = _FakeDerivServer(
            spots=[5800.0, 5800.0],
            entry_spot=5800.0,
            exit_spot=5810.0,
            profit=notional * (5810.0 / 5800.0 - 1.0) - toll_usd,
        )
        down = _FakeDerivServer(
            spots=[5800.0, 5800.0],
            entry_spot=5800.0,
            exit_spot=5790.0,
            profit=notional * (5790.0 / 5800.0 - 1.0) - toll_usd,
        )

        assert _round_trip(up).execution_cost_bps == pytest.approx(
            _round_trip(down).execution_cost_bps
        )
        assert _round_trip(up).execution_cost_bps == pytest.approx(0.745, abs=1e-6)

    def test_adverse_entry_slippage_is_positive_for_a_long(self) -> None:
        """Entrer plus haut que le spot vu à la décision coûte à un MULTUP."""
        server = _FakeDerivServer(
            spots=[5800.0, 5800.0], entry_spot=5801.0, exit_spot=5800.0, profit=0.0
        )

        round_trip = _round_trip(server)

        assert round_trip.entry_slippage_bps == pytest.approx(1.0 / 5800.0 * 10_000.0)
        assert round_trip.entry_slippage_bps > 0

    def test_the_same_drift_is_favourable_to_a_short(self) -> None:
        """Le signe suit le sens de la position, sinon un MULTDOWN se verrait
        facturer un slippage qui l'a en réalité avantagé."""
        server = _FakeDerivServer(
            spots=[5800.0, 5800.0], entry_spot=5801.0, exit_spot=5800.0, profit=0.0
        )

        assert _round_trip(server, direction=-1).entry_slippage_bps < 0

    def test_adverse_exit_slippage_is_positive_for_a_long(self) -> None:
        """Sortir plus bas que le spot vu à la décision coûte à un MULTUP."""
        server = _FakeDerivServer(
            spots=[5800.0, 5800.0], entry_spot=5800.0, exit_spot=5799.0, profit=0.0
        )

        round_trip = _round_trip(server)

        assert round_trip.exit_slippage_bps == pytest.approx(1.0 / 5800.0 * 10_000.0)

    def test_total_cost_adds_slippage_to_execution(self) -> None:
        """C'est ce total, et non le péage seul, qu'une stratégie paie — le
        distinguer est la seule raison d'être de ce script face au relevé
        manuel de l'ADR 0021."""
        server = _FakeDerivServer(
            spots=[5799.0, 5801.0], entry_spot=5800.0, exit_spot=5800.0, profit=-0.0745
        )

        round_trip = _round_trip(server)

        assert round_trip.total_cost_bps == pytest.approx(
            round_trip.execution_cost_bps + round_trip.slippage_bps
        )
        assert round_trip.slippage_bps > 0


class TestCsvOutput:
    def _sample(self, contract_id: int = CONTRACT_ID) -> RoundTrip:
        return RoundTrip(
            opened_at="2026-08-04T12:00:00+00:00",
            symbol=SYMBOL,
            contract_type="MULTUP",
            contract_id=contract_id,
            stake_usd=10.0,
            multiplier=100.0,
            hold_seconds=5.0,
            requested_entry_spot=5800.0,
            entry_spot=5800.0,
            requested_exit_spot=5810.0,
            exit_spot=5810.0,
            realised_pnl_usd=1.6738,
        )

    def test_header_is_written_once_and_rows_are_appended(self, tmp_path: Path) -> None:
        """Append et non écrasement : chaque session est une mesure
        indépendante, et c'est l'accumulation qui dira un jour si le coût dérive."""
        path = tmp_path / "round_trips.csv"

        append_round_trips(path, [self._sample(1)])
        append_round_trips(path, [self._sample(2)])

        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        assert [row["contract_id"] for row in rows] == ["1", "2"]
        assert path.read_text(encoding="utf-8").count("contract_id") == 1

    def test_derived_columns_are_present_and_recomputable(self, tmp_path: Path) -> None:
        """Les colonnes dérivées doivent pouvoir être recalculées depuis les
        colonnes brutes de la même ligne : un CSV qu'on ne peut pas vérifier
        n'est pas une mesure, c'est une affirmation."""
        path = tmp_path / "round_trips.csv"
        append_round_trips(path, [self._sample()])

        row = next(iter(csv.DictReader(path.open(encoding="utf-8"))))
        notional = float(row["stake_usd"]) * float(row["multiplier"])
        gross = notional * (float(row["exit_spot"]) / float(row["entry_spot"]) - 1.0)
        expected = (gross - float(row["realised_pnl_usd"])) / notional * 10_000.0

        assert float(row["notional_usd"]) == pytest.approx(notional)
        assert float(row["execution_cost_bps"]) == pytest.approx(expected, abs=1e-3)

    def test_no_file_is_created_for_an_empty_run(self, tmp_path: Path) -> None:
        """Un CSV vide avec en-tête ressemblerait à une session sans coût
        mesurable plutôt qu'à une session sans trade."""
        path = tmp_path / "round_trips.csv"

        append_round_trips(path, [])

        assert not path.exists()


class TestMalformedResponses:
    """Toute réponse tronquée doit lever, jamais produire une valeur de repli.

    Un coût calculé sur une valeur par défaut serait faux ET crédible : il
    passerait tous les contrôles en aval et fausserait le seuil d'entrée d'un
    modèle sans jamais se signaler.
    """

    def test_ticks_history_without_prices_raises(self) -> None:
        server = _FakeDerivServer()
        server._reply = lambda payload: {  # type: ignore[method-assign]
            "req_id": payload["req_id"],
            "history": {"prices": [], "times": []},
        }

        with pytest.raises(DerivApiError, match="Aucun prix"):
            asyncio.run(DerivTradingClient(server).latest_spot(SYMBOL))

    def test_ticks_history_without_history_block_raises(self) -> None:
        server = _FakeDerivServer()
        server._reply = lambda payload: {"req_id": payload["req_id"]}  # type: ignore[method-assign]

        with pytest.raises(DerivApiError, match="ticks_history"):
            asyncio.run(DerivTradingClient(server).latest_spot(SYMBOL))

    def test_buy_without_contract_id_raises(self) -> None:
        server = _FakeDerivServer()
        server._reply = lambda payload: {  # type: ignore[method-assign]
            "req_id": payload["req_id"],
            "buy": {"buy_price": 10.0},
        }

        with pytest.raises(DerivApiError, match="contract_id"):
            asyncio.run(
                DerivTradingClient(server).buy_multiplier(SYMBOL, 1, 10.0, 100.0)
            )

    def test_sell_without_confirmation_raises(self) -> None:
        server = _FakeDerivServer()
        server._reply = lambda payload: {"req_id": payload["req_id"]}  # type: ignore[method-assign]

        with pytest.raises(DerivApiError, match="Vente"):
            asyncio.run(DerivTradingClient(server).sell(CONTRACT_ID))

    def test_unreadable_contract_raises(self) -> None:
        server = _FakeDerivServer()
        server._reply = lambda payload: {"req_id": payload["req_id"]}  # type: ignore[method-assign]

        with pytest.raises(DerivApiError, match="illisible"):
            asyncio.run(DerivTradingClient(server).open_contract(CONTRACT_ID))

    def test_non_dict_message_is_skipped_not_parsed(self) -> None:
        """Un message JSON qui n'est pas un objet ne porte pas de `req_id` : il
        doit être ignoré comme du bruit, pas faire échouer la requête en cours."""
        server = _FakeDerivServer()
        original_send = server.send

        async def _send_with_garbage(message: str) -> None:
            server._outbound.append(json.dumps(["bruit", 1]))
            await original_send(message)

        server.send = _send_with_garbage  # type: ignore[method-assign]

        assert asyncio.run(DerivTradingClient(server).latest_spot(SYMBOL)) == 5800.0


def _patch_connect(monkeypatch: pytest.MonkeyPatch, server: _FakeDerivServer) -> None:
    monkeypatch.setattr(
        "scripts.measure_deriv_live_round_trip.websockets.connect",
        lambda *a, **k: server,
    )


class TestSession:
    def test_the_websocket_is_opened_on_the_url_returned_by_the_otp(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Aucune URL n'est reconstruite localement : celle de l'OTP porte déjà
        le canal et le jeton de connexion."""
        opened: list[str] = []
        server = _FakeDerivServer(spots=[5800.0] * 10)

        def _record(url: str, *a: object, **k: object) -> _FakeDerivServer:
            opened.append(url)
            return server

        monkeypatch.setattr(
            "scripts.measure_deriv_live_round_trip.websockets.connect", _record
        )

        asyncio.run(
            run_session(
                token=TOKEN,
                app_id=APP_ID,
                symbol=SYMBOL,
                direction=1,
                stake_usd=10.0,
                multiplier=100.0,
                trades=1,
                hold_seconds=0.0,
                csv_path=tmp_path / "out.csv",
                transport=_FakeRestApi().transport,
            )
        )

        assert opened == [DEMO_WS_URL]

    def test_successful_session_writes_every_round_trip(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        server = _FakeDerivServer(spots=[5800.0] * 10, entry_spot=5800.0, exit_spot=5800.0)
        _patch_connect(monkeypatch, server)
        path = tmp_path / "round_trips.csv"

        round_trips = asyncio.run(
            run_session(
                token=TOKEN,
                app_id=APP_ID,
                symbol=SYMBOL,
                direction=1,
                stake_usd=10.0,
                multiplier=100.0,
                trades=3,
                hold_seconds=0.0,
                csv_path=path,
                transport=_FakeRestApi().transport,
            )
        )

        assert len(round_trips) == 3
        assert len(list(csv.DictReader(path.open(encoding="utf-8")))) == 3

    def test_a_failed_round_trip_stops_the_run_but_keeps_the_previous_ones(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Une API qui refuse un ordre refusera probablement le suivant. On
        s'arrête — mais les allers-retours déjà aboutis sont des mesures
        valides et doivent atterrir dans le CSV, pas disparaître avec l'erreur.
        """
        server = _FakeDerivServer(spots=[5800.0] * 10)
        _patch_connect(monkeypatch, server)
        path = tmp_path / "round_trips.csv"

        original_reply = server._reply
        state = {"buys": 0}

        def _fail_on_second_buy(payload: dict[str, Any]) -> dict[str, Any]:
            if "buy" in payload:
                state["buys"] += 1
                if state["buys"] == 2:
                    return {
                        "req_id": payload["req_id"],
                        "error": {"code": "MarketIsClosed", "message": "Market is closed"},
                    }
            return original_reply(payload)

        server._reply = _fail_on_second_buy  # type: ignore[method-assign]

        round_trips = asyncio.run(
            run_session(
                token=TOKEN,
                app_id=APP_ID,
                symbol=SYMBOL,
                direction=1,
                stake_usd=10.0,
                multiplier=100.0,
                trades=5,
                hold_seconds=0.0,
                csv_path=path,
                transport=_FakeRestApi().transport,
            )
        )

        assert len(round_trips) == 1
        assert len(list(csv.DictReader(path.open(encoding="utf-8")))) == 1

    def test_a_live_account_aborts_the_session_before_any_order(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Le refus tombe pendant le préambule REST : aucun WebSocket n'est même
        ouvert, donc aucun ordre ne peut partir."""
        server = _FakeDerivServer()
        _patch_connect(monkeypatch, server)

        with pytest.raises(LiveAccountRefused):
            asyncio.run(
                run_session(
                    token=TOKEN,
                    app_id=APP_ID,
                    symbol=SYMBOL,
                    direction=1,
                    stake_usd=10.0,
                    multiplier=100.0,
                    trades=5,
                    hold_seconds=0.0,
                    csv_path=tmp_path / "round_trips.csv",
                    transport=_FakeRestApi(accounts=[REAL_ACCOUNT]).transport,
                )
            )

        assert server.requests == []


def _patch_rest(monkeypatch: pytest.MonkeyPatch, api: _FakeRestApi) -> None:
    """Injecte le préambule REST doublé dans le `run_session` réel.

    `main()` n'expose pas de transport — le lui ajouter serait un paramètre de
    production dont seuls les tests se serviraient. On enveloppe donc l'appel,
    ce qui laisse `main()` et `run_session` s'exécuter tels quels et garde les
    codes de sortie authentiques.
    """
    module = "scripts.measure_deriv_live_round_trip"
    real = run_session

    async def _with_transport(**kwargs: Any) -> Any:
        return await real(transport=api.transport, **kwargs)

    monkeypatch.setattr(f"{module}.run_session", _with_transport)


class TestCli:
    """Les codes de sortie distinguent les causes : un compte réel refusé n'est
    pas la même chose qu'une API en panne, et un script d'instrumentation doit
    pouvoir être enchaîné dans un shell sans lire ses logs."""

    @pytest.fixture(autouse=True)
    def _isolate_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Sans ça, `load_dotenv()` lirait le `.env` réel du dépôt et les tests
        # dépendraient des identifiants présents sur la machine.
        monkeypatch.setattr(
            "scripts.measure_deriv_live_round_trip.load_dotenv", lambda *a, **k: False
        )
        monkeypatch.delenv("DERIV_API_TOKEN", raising=False)
        monkeypatch.delenv("DERIV_APP_ID", raising=False)

    def test_out_of_bounds_stake_exits_before_touching_the_network(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _forbidden(*_a: object, **_k: object) -> None:
            raise AssertionError("aucune connexion ne doit être ouverte")

        monkeypatch.setattr(
            "scripts.measure_deriv_live_round_trip.websockets.connect", _forbidden
        )

        assert main(["--stake", str(MAX_STAKE_USD + 1)]) == 2

    def test_missing_token_exits_without_connecting(self) -> None:
        assert main([]) == 2

    def test_missing_app_id_exits_without_connecting(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """La nouvelle API rejette tout PAT sans `Deriv-App-ID`. Partir sans lui
        échouerait au premier appel REST — autant le dire avant."""
        monkeypatch.setenv("DERIV_API_TOKEN", TOKEN)

        assert main([]) == 2

    def test_live_account_exits_with_its_own_code(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("DERIV_API_TOKEN", TOKEN)
        monkeypatch.setenv("DERIV_APP_ID", APP_ID)
        _patch_rest(monkeypatch, _FakeRestApi(accounts=[REAL_ACCOUNT]))
        _patch_connect(monkeypatch, _FakeDerivServer())

        assert main(["--csv", str(tmp_path / "out.csv"), "--trades", "1"]) == 3

    def test_rest_refusal_exits_with_the_api_code(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("DERIV_API_TOKEN", TOKEN)
        monkeypatch.setenv("DERIV_APP_ID", APP_ID)
        _patch_rest(
            monkeypatch,
            _FakeRestApi(accounts_status=401, accounts_body="Invalid application"),
        )
        _patch_connect(monkeypatch, _FakeDerivServer())

        assert main(["--csv", str(tmp_path / "out.csv"), "--trades", "1"]) == 4

    def test_successful_run_exits_zero_and_writes_the_csv(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("DERIV_API_TOKEN", TOKEN)
        monkeypatch.setenv("DERIV_APP_ID", APP_ID)
        _patch_rest(monkeypatch, _FakeRestApi())
        _patch_connect(monkeypatch, _FakeDerivServer(spots=[5800.0] * 10))
        path = tmp_path / "out.csv"

        assert main(["--csv", str(path), "--trades", "2", "--hold", "0"]) == 0
        assert len(list(csv.DictReader(path.open(encoding="utf-8")))) == 2

    def test_an_explicit_account_id_reaches_the_selection(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """`--account-id` est le seul moyen de trancher entre deux comptes démo
        actifs : s'il n'était pas transmis, la session resterait bloquée."""
        monkeypatch.setenv("DERIV_API_TOKEN", TOKEN)
        monkeypatch.setenv("DERIV_APP_ID", APP_ID)
        second = {**DEMO_ACCOUNT, "account_id": "VRTC5678"}
        _patch_rest(monkeypatch, _FakeRestApi(accounts=[DEMO_ACCOUNT, second]))
        _patch_connect(monkeypatch, _FakeDerivServer(spots=[5800.0] * 10))
        path = tmp_path / "out.csv"

        exit_code = main(
            ["--csv", str(path), "--trades", "1", "--hold", "0", "--account-id", "VRTC5678"]
        )

        assert exit_code == 0

    def test_a_run_without_any_round_trip_is_not_a_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Zéro aller-retour abouti ne doit pas sortir 0 : un shell qui enchaîne
        sur ce code croirait avoir une mesure."""
        monkeypatch.setenv("DERIV_API_TOKEN", TOKEN)
        monkeypatch.setenv("DERIV_APP_ID", APP_ID)
        _patch_rest(monkeypatch, _FakeRestApi())
        _patch_connect(monkeypatch, _FakeDerivServer(errors={"buy": "MarketIsClosed"}))

        assert main(["--csv", str(tmp_path / "out.csv"), "--trades", "1", "--hold", "0"]) == 1

    def test_summarise_handles_an_empty_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        summarise([])

        assert "Aucun aller-retour" in capsys.readouterr().out
