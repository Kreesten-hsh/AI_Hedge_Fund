"""Lot 2E — bandes de Bollinger dans l'unique implémentation d'indicateurs.

`VolatilityAgent` lit `bb_upper` et `bb_lower`. Aucun des deux n'existait :
l'agent votait donc `WAIT 0.0` sur tous les ticks, quelle que soit la
volatilité réelle.

Les bandes sont ajoutées à `TechnicalFeatureExtractor` et nulle part ailleurs.
Les calculer dans l'orchestrateur ou dans l'agent créerait une cinquième
implémentation d'indicateurs alors que le Lot 3 doit en supprimer trois.
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


def _bars(closes: list[str]) -> list[MarketBar]:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars = []
    for index, close in enumerate(closes):
        price = Decimal(close)
        bars.append(
            MarketBar(
                symbol=SYMBOL,
                timeframe=TimeFrame.M1,
                timestamp=base + timedelta(minutes=index),
                open=price,
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                close=price,
                volume=Decimal("1000"),
            )
        )
    return bars


class TestBollingerBandsAreDeclared:
    def test_metadata_exposes_the_three_bands(self) -> None:
        names = [m.name for m in TechnicalFeatureExtractor().get_metadata()]

        assert "bb_upper" in names
        assert "bb_middle" in names
        assert "bb_lower" in names

    def test_bands_are_declared_as_volatility_features(self) -> None:
        meta = {m.name: m for m in TechnicalFeatureExtractor().get_metadata()}

        assert meta["bb_upper"].group.value == "volatility"
        assert meta["bb_upper"].parameters == {"period": 20, "std_dev": 2.0}


class TestBollingerBandsAreCorrect:
    def test_middle_band_is_the_twenty_period_average(self) -> None:
        # 20 clôtures constantes à 100 : la moyenne vaut 100.
        features = TechnicalFeatureExtractor().extract(_bars(["100"] * 20))

        assert features[19].features["bb_middle"] == pytest.approx(100.0)

    def test_bands_collapse_on_the_average_when_there_is_no_dispersion(self) -> None:
        """Écart-type nul => bandes confondues avec la moyenne.

        C'est le cas dégénéré qui distingue un vrai calcul d'une constante :
        une constante arbitraire ne se refermerait pas.
        """
        features = TechnicalFeatureExtractor().extract(_bars(["100"] * 20))
        row = features[19].features

        assert row["bb_upper"] == pytest.approx(100.0)
        assert row["bb_lower"] == pytest.approx(100.0)

    def test_bands_widen_with_dispersion(self) -> None:
        closes = [str(100 + (10 if index % 2 else -10)) for index in range(20)]
        features = TechnicalFeatureExtractor().extract(_bars(closes))
        row = features[19].features

        assert row["bb_upper"] > row["bb_middle"] > row["bb_lower"]

    def test_upper_band_is_two_standard_deviations_above_the_mean(self) -> None:
        closes = [str(100 + index) for index in range(20)]
        features = TechnicalFeatureExtractor().extract(_bars(closes))
        row = features[19].features

        # std_20 est déjà produit par l'extracteur : les bandes doivent en
        # dériver, sinon deux mesures de dispersion divergeraient dans le même
        # FeatureSet.
        assert row["bb_upper"] == pytest.approx(row["bb_middle"] + 2.0 * row["std_20"])
        assert row["bb_lower"] == pytest.approx(row["bb_middle"] - 2.0 * row["std_20"])

    def test_bands_are_none_during_burn_in(self) -> None:
        """Avant 20 barres, la dispersion n'est pas définie.

        Renvoyer 0.0 ferait croire à une volatilité nulle et collerait le prix
        sur les bandes : le VolatilityAgent voterait sur du vide.
        """
        features = TechnicalFeatureExtractor().extract(_bars(["100"] * 5))

        assert features[4].features["bb_upper"] is None
        assert features[4].features["bb_lower"] is None
