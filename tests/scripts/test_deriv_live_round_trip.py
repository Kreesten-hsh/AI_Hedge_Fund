"""Client d'aller-retours Multipliers Deriv : garde-fous, appariement, coûts.

Ce script route des ordres sans passer par le `RiskEngine` — c'est la raison
pour laquelle il vit dans `scripts/`. Les tests ci-dessous couvrent donc en
priorité ce qui remplace le risk check absent : refus d'un compte réel, plafonds
de mise et de volume, fermeture garantie d'une position ouverte.

Aucun réseau : la connexion est doublée et répond à partir du contenu de la
requête, `req_id` compris. Le protocole n'est pas raccourci pour autant.
"""

from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.measure_deriv_live_round_trip import (
    MAX_HOLD_SECONDS,
    MAX_STAKE_USD,
    MAX_TRADES_PER_RUN,
    DerivApiError,
    DerivTradingClient,
    LiveAccountRefused,
    RoundTrip,
    append_round_trips,
    main,
    run_round_trip,
    run_session,
    summarise,
    validate_run_parameters,
)

SYMBOL = "CRASH1000"
CONTRACT_ID = 987654321


class _FakeDerivServer:
    """Connexion doublée qui répond en fonction de la requête reçue.

    Répondre au contenu et non à un ordre d'appel figé : c'est ce qui permet
    d'exercer l'appariement par `req_id` et les erreurs ciblées sans réécrire
    une file de messages à chaque test.
    """

    def __init__(
        self,
        *,
        is_virtual: int | None = 1,
        spots: list[float] | None = None,
        entry_spot: float = 5800.0,
        exit_spot: float = 5800.0,
        profit: float = -0.06,
        settled_extra: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
        noise_before_reply: int = 0,
    ) -> None:
        self.is_virtual = is_virtual
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

        if "authorize" in payload:
            account: dict[str, Any] = {
                "loginid": "VRTC1234" if self.is_virtual else "CR1234",
                "currency": "USD",
                "balance": 10_000.0,
            }
            # `None` = champ absent de la réponse, cas distinct de `is_virtual: 0`.
            if self.is_virtual is not None:
                account["is_virtual"] = self.is_virtual
            return {"req_id": req_id, "authorize": account}
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


class TestDemoAccountGuard:
    def test_live_account_is_refused_before_any_order(self) -> None:
        """Le refus doit intervenir à l'authentification, pas plus tard.

        Ce script contourne le `RiskEngine` par construction : un ordre passé
        sur un compte financé n'aurait aucun garde-fou en aval.
        """
        server = _FakeDerivServer(is_virtual=0)

        with pytest.raises(LiveAccountRefused, match="is_virtual"):
            asyncio.run(DerivTradingClient(server).authorize("token"))

        assert all("buy" not in request for request in server.requests)

    def test_missing_is_virtual_field_is_refused(self) -> None:
        """Champ absent = non virtuel. Un défaut permissif transformerait une
        réponse tronquée en autorisation de trader en réel."""
        server = _FakeDerivServer(is_virtual=None)

        with pytest.raises(LiveAccountRefused):
            asyncio.run(DerivTradingClient(server).authorize("token"))

    def test_virtual_account_is_accepted(self) -> None:
        account = asyncio.run(DerivTradingClient(_FakeDerivServer()).authorize("token"))

        assert account["is_virtual"] == 1
        assert account["loginid"] == "VRTC1234"


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

    def test_authorize_without_account_block_raises(self) -> None:
        server = _FakeDerivServer()
        server._reply = lambda payload: {"req_id": payload["req_id"]}  # type: ignore[method-assign]

        with pytest.raises(DerivApiError, match="authorize"):
            asyncio.run(DerivTradingClient(server).authorize("token"))

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
    def test_successful_session_writes_every_round_trip(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        server = _FakeDerivServer(spots=[5800.0] * 10, entry_spot=5800.0, exit_spot=5800.0)
        _patch_connect(monkeypatch, server)
        path = tmp_path / "round_trips.csv"

        round_trips = asyncio.run(
            run_session(
                token="token",
                symbol=SYMBOL,
                direction=1,
                stake_usd=10.0,
                multiplier=100.0,
                trades=3,
                hold_seconds=0.0,
                csv_path=path,
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
                token="token",
                symbol=SYMBOL,
                direction=1,
                stake_usd=10.0,
                multiplier=100.0,
                trades=5,
                hold_seconds=0.0,
                csv_path=path,
            )
        )

        assert len(round_trips) == 1
        assert len(list(csv.DictReader(path.open(encoding="utf-8")))) == 1

    def test_a_live_account_aborts_the_session_before_any_order(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        server = _FakeDerivServer(is_virtual=0)
        _patch_connect(monkeypatch, server)

        with pytest.raises(LiveAccountRefused):
            asyncio.run(
                run_session(
                    token="token",
                    symbol=SYMBOL,
                    direction=1,
                    stake_usd=10.0,
                    multiplier=100.0,
                    trades=5,
                    hold_seconds=0.0,
                    csv_path=tmp_path / "round_trips.csv",
                )
            )

        assert all("buy" not in request for request in server.requests)


class TestCli:
    """Les codes de sortie distinguent les causes : un compte réel refusé n'est
    pas la même chose qu'une API en panne, et un script d'instrumentation doit
    pouvoir être enchaîné dans un shell sans lire ses logs."""

    @pytest.fixture(autouse=True)
    def _isolate_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Sans ça, `load_dotenv()` lirait le `.env` réel du dépôt et les tests
        # dépendraient du token présent sur la machine.
        monkeypatch.setattr(
            "scripts.measure_deriv_live_round_trip.load_dotenv", lambda *a, **k: False
        )
        monkeypatch.delenv("DERIV_API_TOKEN", raising=False)

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

    def test_live_account_exits_with_its_own_code(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("DERIV_API_TOKEN", "token")
        _patch_connect(monkeypatch, _FakeDerivServer(is_virtual=0))

        assert main(["--csv", str(tmp_path / "out.csv"), "--trades", "1"]) == 3

    def test_api_error_exits_with_its_own_code(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("DERIV_API_TOKEN", "token")
        _patch_connect(monkeypatch, _FakeDerivServer(errors={"authorize": "InvalidToken"}))

        assert main(["--csv", str(tmp_path / "out.csv"), "--trades", "1"]) == 4

    def test_successful_run_exits_zero_and_writes_the_csv(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("DERIV_API_TOKEN", "token")
        _patch_connect(monkeypatch, _FakeDerivServer(spots=[5800.0] * 10))
        path = tmp_path / "out.csv"

        assert main(["--csv", str(path), "--trades", "2", "--hold", "0"]) == 0
        assert len(list(csv.DictReader(path.open(encoding="utf-8")))) == 2

    def test_a_run_without_any_round_trip_is_not_a_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Zéro aller-retour abouti ne doit pas sortir 0 : un shell qui enchaîne
        sur ce code croirait avoir une mesure."""
        monkeypatch.setenv("DERIV_API_TOKEN", "token")
        _patch_connect(monkeypatch, _FakeDerivServer(errors={"buy": "MarketIsClosed"}))

        assert main(["--csv", str(tmp_path / "out.csv"), "--trades", "1", "--hold", "0"]) == 1

    def test_summarise_handles_an_empty_run(self, capsys: pytest.CaptureFixture[str]) -> None:
        summarise([])

        assert "Aucun aller-retour" in capsys.readouterr().out
