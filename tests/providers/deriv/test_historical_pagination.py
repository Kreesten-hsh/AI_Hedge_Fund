"""Pagination de l'historique de bougies Deriv.

Le plafond de 5000 bougies par requête est une limite du serveur, pas un défaut
d'appel : demander `count=20000` renvoie 5000. La seule route pour dépasser est
de reculer `end` dans le temps et de recoller les blocs.

Protocole vérifié sur la forme documentée des réponses `ticks_history`, avec une
connexion doublée : aucun réseau, mais aucun raccourci non plus sur le format.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest

from aegis_trade.providers.deriv.historical_data import (
    MAX_CANDLES_PER_REQUEST,
    DerivHistoricalData,
)

SYMBOL = "CRASH1000"
# Époque arbitraire mais fixe : une date figée rend les assertions lisibles et
# la suite reproductible.
BASE_EPOCH = 1_770_000_000


class _FakeConnection:
    """Connexion WebSocket doublée : répond depuis une file, enregistre les envois."""

    def __init__(self, inbound: list[str]) -> None:
        self.inbound = list(inbound)
        self.sent: list[dict[str, Any]] = []

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    async def recv(self) -> str:
        if not self.inbound:
            raise ConnectionError("flux terminé")
        return self.inbound.pop(0)

    async def __aenter__(self) -> "_FakeConnection":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None


def _candles_message(start_epoch: int, count: int, granularity: int = 60) -> str:
    """Réponse `ticks_history` en style candles, prix croissants et distincts."""
    return json.dumps(
        {
            "echo_req": {"ticks_history": SYMBOL, "style": "candles"},
            "msg_type": "candles",
            "candles": [
                {
                    "epoch": start_epoch + i * granularity,
                    "open": 5800.0 + i,
                    "high": 5801.0 + i,
                    "low": 5799.0 + i,
                    "close": 5800.5 + i,
                }
                for i in range(count)
            ],
        }
    )


def _patch_connect(monkeypatch: pytest.MonkeyPatch, blocks: list[str]) -> _FakeConnection:
    """Branche une connexion doublée qui sert `blocks` sur des appels successifs."""
    connection = _FakeConnection(blocks)
    monkeypatch.setattr(
        "aegis_trade.providers.deriv.historical_data.websockets.connect",
        lambda *a, **k: connection,
    )
    return connection


class TestPagination:
    def test_blocks_are_concatenated_in_chronological_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deriv sert du plus récent au plus ancien ; le résultat doit être croissant.

        Un DataFrame non trié casserait silencieusement `build_feature_sets`, qui
        suppose l'ordre chronologique pour calculer des rendements.
        """
        recent = _candles_message(BASE_EPOCH + 6000 * 60, 100)
        older = _candles_message(BASE_EPOCH, 100)
        connection = _patch_connect(monkeypatch, [recent, older])

        df = DerivHistoricalData().fetch_candles_paginated_sync(
            symbol=SYMBOL, target_count=200, granularity=60, page_size=100
        )

        assert len(df) == 200
        assert df["timestamp"].is_monotonic_increasing
        assert len(connection.sent) == 2

    def test_second_request_ends_before_the_oldest_bar_received(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`end` recule d'une granularité sous la plus ancienne barre reçue.

        Réutiliser cette barre comme `end` la renverrait en doublon ; reculer de
        plus d'une granularité ouvrirait un trou dans la série.
        """
        connection = _patch_connect(
            monkeypatch,
            [_candles_message(BASE_EPOCH + 6000 * 60, 100), _candles_message(BASE_EPOCH, 100)],
        )

        DerivHistoricalData().fetch_candles_paginated_sync(
            symbol=SYMBOL, target_count=200, granularity=60, page_size=100
        )

        assert connection.sent[0]["end"] == "latest"
        assert connection.sent[1]["end"] == str(BASE_EPOCH + 6000 * 60 - 60)

    def test_overlapping_blocks_are_deduplicated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deriv peut renvoyer des barres déjà vues : la même bougie ne doit pas
        compter deux fois, sinon les rendements calculés dessus valent zéro."""
        first = _candles_message(BASE_EPOCH + 50 * 60, 100)
        overlapping = _candles_message(BASE_EPOCH, 100)  # 50 barres communes
        _patch_connect(monkeypatch, [first, overlapping])

        df = DerivHistoricalData().fetch_candles_paginated_sync(
            symbol=SYMBOL, target_count=200, granularity=60, page_size=100
        )

        assert len(df) == 150
        assert not df["timestamp"].duplicated().any()

    def test_stops_when_the_server_stops_sending_new_bars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Historique épuisé : le serveur renvoie les mêmes barres indéfiniment.

        Sans cette sortie, la boucle tournerait jusqu'à `target_count` en
        martelant l'API pour zéro donnée nouvelle.
        """
        block = _candles_message(BASE_EPOCH, 100)
        connection = _patch_connect(monkeypatch, [block, block, block, block])

        df = DerivHistoricalData().fetch_candles_paginated_sync(
            symbol=SYMBOL, target_count=10_000, granularity=60, page_size=100
        )

        assert len(df) == 100
        # Une requête utile, une qui ne rapporte rien et arrête la boucle.
        assert len(connection.sent) == 2

    def test_empty_first_block_returns_an_empty_frame(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_connect(monkeypatch, [_candles_message(BASE_EPOCH, 0)])

        df = DerivHistoricalData().fetch_candles_paginated_sync(
            symbol=SYMBOL, target_count=5000, granularity=60, page_size=100
        )

        assert df.empty
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]

    def test_result_is_trimmed_to_the_requested_count(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Le dernier bloc dépasse la cible : on garde les plus RÉCENTES.

        Tronquer par la fin jetterait les barres les plus proches du présent,
        qui sont celles qui comptent pour valider un modèle destiné à trader.
        """
        _patch_connect(
            monkeypatch,
            [_candles_message(BASE_EPOCH + 100 * 60, 100), _candles_message(BASE_EPOCH, 100)],
        )

        df = DerivHistoricalData().fetch_candles_paginated_sync(
            symbol=SYMBOL, target_count=150, granularity=60, page_size=100
        )

        assert len(df) == 150
        latest = datetime.fromtimestamp(BASE_EPOCH + 199 * 60, tz=timezone.utc)
        assert df["timestamp"].iloc[-1] == latest

    def test_page_size_above_the_server_cap_is_refused(self) -> None:
        """5000 est une limite serveur : demander plus renvoie 5000 sans le dire.
        Échouer bruyamment vaut mieux qu'une pagination qui croit avancer de 20000."""
        with pytest.raises(ValueError, match="5000"):
            DerivHistoricalData().fetch_candles_paginated_sync(
                symbol=SYMBOL, target_count=10_000, page_size=MAX_CANDLES_PER_REQUEST + 1
            )

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"page_size": 0},
            {"target_count": 0},
            {"granularity": 0},
            {"page_size": -1},
            {"target_count": -100},
            {"granularity": -60},
        ],
    )
    def test_non_positive_parameters_are_refused(self, kwargs: dict[str, int]) -> None:
        """Zéro ou négatif ne dégrade pas gracieusement : `target_count=0` rendrait
        un DataFrame vide qui ressemble à un symbole sans historique, et
        `granularity=0` ferait stagner le curseur `end` sur la même page à
        l'infini. Refuser à l'entrée plutôt que produire un jeu faux ou boucler."""
        params: dict[str, int] = {"target_count": 200, "granularity": 60, "page_size": 100}
        params.update(kwargs)
        with pytest.raises(ValueError, match=">= 1"):
            DerivHistoricalData().fetch_candles_paginated_sync(symbol=SYMBOL, **params)

    def test_api_error_is_raised_not_swallowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Une erreur API en cours de pagination doit remonter : renvoyer un
        historique partiel silencieusement produirait un jeu tronqué qui passerait
        pour complet."""
        _patch_connect(
            monkeypatch,
            [
                _candles_message(BASE_EPOCH + 100 * 60, 100),
                json.dumps({"error": {"code": "InvalidSymbol", "message": "Symbol not found"}}),
            ],
        )

        with pytest.raises(RuntimeError, match="Symbol not found"):
            DerivHistoricalData().fetch_candles_paginated_sync(
                symbol=SYMBOL, target_count=200, granularity=60, page_size=100
            )

    def test_partial_page_does_not_stop_pagination_if_new_bars_exist(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Une page intermédiaire comportant moins de bougies qu'une page pleine (ex: tranche de début de semaine)
        ne doit pas arrêter la pagination tant que de nouvelles barres inédites sont reçues (added > 0).
        """
        page1 = _candles_message(BASE_EPOCH + 2000 * 60, 500)   # Page partielle (500 barres)
        page2 = _candles_message(BASE_EPOCH, 1000)             # Page suivante (1000 barres)
        connection = _patch_connect(monkeypatch, [page1, page2])

        df = DerivHistoricalData().fetch_candles_paginated_sync(
            symbol="frxXAUUSD", target_count=1500, granularity=60, page_size=5000
        )

        assert len(df) == 1500
        assert len(connection.sent) == 2


    def test_weekend_snapping_skips_market_close(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Quand le plus ancien timestamp d'un bloc est Lundi 00:00:00 UTC,
        le curseur end du bloc suivant doit sauter le week-end et viser le Vendredi précédent à 20:59:00 UTC.
        """
        from aegis_trade.providers.deriv.historical_data import _is_weekend_close, _snap_to_friday_close

        # Lundi 2026-08-03 00:00:00 UTC
        monday_dt = datetime(2026, 8, 3, 0, 0, 0, tzinfo=timezone.utc)
        monday_epoch = int(monday_dt.timestamp())

        # Dimanche 2026-08-02 23:59:00 UTC (recul de 60s) -> est en week-end
        sunday_dt = datetime.fromtimestamp(monday_epoch - 60, tz=timezone.utc)
        assert _is_weekend_close(sunday_dt) is True

        # Snap au vendredi précédent -> 2026-07-31 20:59:00 UTC
        snapped_dt = _snap_to_friday_close(sunday_dt)
        assert snapped_dt == datetime(2026, 7, 31, 20, 59, 0, tzinfo=timezone.utc)

        # Simulation de pagination avec un bloc démarrant lundi 00:00
        page1 = _candles_message(monday_epoch, 100)  # Lundi 00:00 -> 01:40
        page2 = _candles_message(int(snapped_dt.timestamp()) - 100 * 60, 100)
        connection = _patch_connect(monkeypatch, [page1, page2])

        df = DerivHistoricalData().fetch_candles_paginated_sync(
            symbol="frxXAUUSD", target_count=200, granularity=60, page_size=100
        )

        assert len(df) == 200
        assert connection.sent[1]["end"] == str(int(snapped_dt.timestamp()))

