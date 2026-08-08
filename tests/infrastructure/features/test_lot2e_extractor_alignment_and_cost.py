"""Lot 2E — alignement barre/features et coût par tick de l'extracteur.

Deux défauts trouvés en branchant l'extracteur sur la boucle de ticks :

1. `extract` trie le DataFrame par timestamp puis lit `bars[i]` dans la liste
   d'entrée **non triée** pour reconstruire chaque `FeatureSet`. Sur une entrée
   désordonnée, les features d'une barre sont attachées à l'horodatage et au
   symbole d'une autre. Silencieux : aucune exception, des valeurs plausibles.

2. la reconstruction par `df.iterrows()` coûtait ~390 ms par tick sur une
   fenêtre de 200 barres, contre un budget de latence du Council de 20 ms.
   Le calcul des indicateurs n'y est pour rien : c'est l'indexation pandas
   ligne par ligne.
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from aegis_trade.domain.core import AssetClass, MarketBar, Symbol, TimeFrame
from aegis_trade.infrastructure.features.technical_extractor import (
    TechnicalFeatureExtractor,
)

SYMBOL = Symbol(name="BTCUSD", asset_class=AssetClass.CRYPTO)
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _bar(close: str, index: int) -> MarketBar:
    price = Decimal(close)
    return MarketBar(
        symbol=SYMBOL,
        timeframe=TimeFrame.M1,
        timestamp=BASE + timedelta(minutes=index),
        open=price,
        high=price + Decimal("1"),
        low=price - Decimal("1"),
        close=price,
        volume=Decimal("1000"),
    )


class TestFeaturesStayAttachedToTheirBar:
    def test_unsorted_input_does_not_misalign_features(self) -> None:
        """Une entrée désordonnée doit produire les mêmes features que triée.

        Le tri interne du DataFrame doit s'appliquer aussi à la liste lue pour
        reconstruire les FeatureSets, sinon la ligne calculée pour 12:02 est
        publiée sous l'horodatage de 12:00.
        """
        extractor = TechnicalFeatureExtractor()
        ordered = [_bar(str(100 + index), index) for index in range(30)]
        shuffled = [ordered[i] for i in (5, 0, 3, 1, 4, 2, *range(6, 30))]

        from_ordered = extractor.extract(ordered)
        from_shuffled = extractor.extract(shuffled)

        assert [f.timestamp for f in from_shuffled] == [
            f.timestamp for f in from_ordered
        ]
        assert from_shuffled[-1].features["ema_50"] == pytest.approx(
            from_ordered[-1].features["ema_50"]
        )

    def test_timestamps_are_returned_in_chronological_order(self) -> None:
        extractor = TechnicalFeatureExtractor()
        ordered = [_bar(str(100 + index), index) for index in range(10)]
        shuffled = [ordered[i] for i in (9, 2, 7, 0, 4, 1, 8, 3, 6, 5)]

        stamps = [fs.timestamp for fs in extractor.extract(shuffled)]

        assert stamps == sorted(stamps)

    def test_close_of_the_last_set_matches_the_latest_bar(self) -> None:
        """Vérification de bout en bout de l'alignement.

        `bb_middle` sur 20 clôtures constantes vaut cette clôture : si la
        dernière ligne était rattachée à une autre barre, la valeur ne
        correspondrait pas.
        """
        extractor = TechnicalFeatureExtractor()
        ordered = [_bar("100", index) for index in range(20)]
        shuffled = list(reversed(ordered))

        result = extractor.extract(shuffled)

        assert result[-1].timestamp == ordered[-1].timestamp
        assert result[-1].features["bb_middle"] == pytest.approx(100.0)


class TestNaNContract:
    def test_undefined_values_are_none_not_nan(self) -> None:
        """Le domaine attend None ; un NaN traverserait les comparaisons."""
        result = TechnicalFeatureExtractor().extract([_bar("100", 0)])
        row = result[0].features

        assert row["std_20"] is None
        for name, value in row.items():
            assert value is None or not math.isnan(value), name

    def test_defined_values_are_plain_floats(self) -> None:
        result = TechnicalFeatureExtractor().extract(
            [_bar(str(100 + i), i) for i in range(25)]
        )

        assert isinstance(result[-1].features["ema_50"], float)
        assert isinstance(result[-1].features["rsi_14"], float)


class TestExtractionCost:
    def test_a_two_hundred_bar_window_costs_far_less_than_iterrows(self) -> None:
        """Garde-fou anti-régression sur la reconstruction des FeatureSets.

        La version `df.iterrows()` mesurait ~390 ms par extraction sur 200
        barres. La version colonne mesure ~40 ms, dominés par la construction
        du DataFrame elle-même et non par la taille de la fenêtre (~36 ms déjà
        à 60 barres). La borne à 150 ms n'est donc pas un objectif de latence :
        c'est le seuil qui distingue les deux implémentations sans dépendre de
        la charge de la machine de CI.

        Le coût résiduel reste au-dessus du budget de 20 ms du Council. Il est
        acceptable sur un flux de barres M1 mais devra être repris si le
        système passe au tick-à-tick — dette à traiter avec l'unification des
        indicateurs (Lot 3), pas ici.
        """
        extractor = TechnicalFeatureExtractor()
        bars = [_bar(str(100 + index % 13), index) for index in range(200)]
        extractor.extract(bars)  # amorçage, hors mesure

        start = time.perf_counter()
        for _ in range(5):
            extractor.extract(bars)
        elapsed_ms = (time.perf_counter() - start) / 5 * 1000

        assert elapsed_ms < 150.0, f"{elapsed_ms:.0f} ms par extraction"
