"""Lot 2E — `ema_distance`, seule clé du contrat lue hors des 8 agents.

`application/monitoring/engine.py:183` lit `ema_distance` dans le contexte
d'ouverture du trade, puis le place dans l'embedding de l'`Experience` :

    embedding=(rsi, ema_distance, atr)

Cet embedding alimente DBSCAN, qui alimente `KnowledgeGenerator`, dont le
`PatternAgent` relit les patterns pour voter. La clé revient donc dans la
décision de trading : un axe constant y rend un tiers de l'espace de
clustering inerte, et deux trades opposés paraissent voisins.

Avant ce lot, l'orchestrateur injectait `ema_distance: 0.1` constant. Retirer
la clé sans la remplacer ferait tomber le lecteur sur son repli `0.0` : un
placeholder échangé contre un autre, ce que ce lot supprime précisément.

La valeur est produite par l'extracteur et nulle part ailleurs : la calculer
dans l'orchestrateur ou dans le fournisseur ajouterait une implémentation
d'indicateur aux quatre que le Lot 3 doit unifier.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from aegis_trade.domain.core import AssetClass, MarketBar, Symbol, TimeFrame
from aegis_trade.infrastructure.features.technical_extractor import (
    TechnicalFeatureExtractor,
)

SYMBOL = Symbol(name="BTCUSD", asset_class=AssetClass.CRYPTO)
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _bars(closes: list[str]) -> list[MarketBar]:
    bars = []
    for index, close in enumerate(closes):
        price = Decimal(close)
        bars.append(
            MarketBar(
                symbol=SYMBOL,
                timeframe=TimeFrame.M1,
                timestamp=BASE + timedelta(minutes=index),
                open=price,
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                close=price,
                volume=Decimal("1000"),
            )
        )
    return bars


class TestEmaDistanceIsDeclared:
    def test_metadata_exposes_the_feature(self) -> None:
        names = [m.name for m in TechnicalFeatureExtractor().get_metadata()]

        assert "ema_distance" in names

    def test_it_is_declared_as_a_trend_feature_on_the_fifty_period_average(
        self,
    ) -> None:
        meta = {m.name: m for m in TechnicalFeatureExtractor().get_metadata()}

        assert meta["ema_distance"].group.value == "trend"
        assert meta["ema_distance"].parameters == {"period": 50}


class TestEmaDistanceIsComputed:
    def test_it_is_the_relative_gap_to_the_fifty_period_ema(self) -> None:
        bars = _bars([str(100 + index) for index in range(60)])
        row = TechnicalFeatureExtractor().extract(bars)[-1].features

        close = float(bars[-1].close)
        expected = (close - row["ema_50"]) / row["ema_50"]
        assert row["ema_distance"] == pytest.approx(expected)

    def test_it_is_positive_above_the_average(self) -> None:
        row = TechnicalFeatureExtractor().extract(
            _bars([str(100 + index) for index in range(60)])
        )[-1].features

        assert row["ema_distance"] > 0.0

    def test_it_is_negative_below_the_average(self) -> None:
        row = TechnicalFeatureExtractor().extract(
            _bars([str(200 - index) for index in range(60)])
        )[-1].features

        assert row["ema_distance"] < 0.0

    def test_a_flat_market_gives_a_zero_that_is_measured_not_defaulted(self) -> None:
        """Sur 30 clôtures identiques l'écart vaut réellement zéro.

        Ce cas est indistinguable d'un repli à `0.0` du point de vue de la
        valeur : c'est le test négatif (`test_it_is_positive_above_the_average`)
        qui prouve que le calcul existe. Celui-ci vérifie qu'un marché plat ne
        produit ni NaN ni division par zéro.
        """
        row = TechnicalFeatureExtractor().extract(_bars(["100"] * 30))[-1].features

        assert row["ema_distance"] == pytest.approx(0.0)
