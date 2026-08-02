"""Adaptateur Qlib — chaîne réelle DatasetBuilder → LightGBM → Predictor → Stratégie.

Le mock LightGBM (sortie constante 0.55) a été supprimé : ces tests s'exécutent
sur un vrai `lightgbm.train`. Ils vérifient trois propriétés qu'un mock ne pouvait
pas porter : l'absence de fuite de la cible, l'échec bruyant sur données
insuffisantes ou désalignées, et la direction du signal issue d'un rendement
attendu (et non d'une probabilité).
"""

from datetime import datetime, timedelta, timezone
from typing import List

import pytest

from aegis_trade.application.strategy.ml_strategy import MLStrategy
from aegis_trade.domain.core import AssetClass, Symbol, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.providers.qlib.dataset_builder import (
    TARGET_COLUMN,
    DatasetBuilder,
)
from aegis_trade.providers.qlib.model_factory import ModelFactory, _feature_matrix
from aegis_trade.providers.qlib.predictor import QlibPredictor
from aegis_trade.providers.qlib.trainer import QlibTrainer

SYMBOL = Symbol("CRASH1000", AssetClass.INDICES)
ORIGIN = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _feature_sets(closes: List[float]) -> List[FeatureSet]:
    """FeatureSets minimalistes mais réalistes : prix + features dérivées.

    `close_price` est requis par DatasetBuilder pour construire le label forward
    (et lu par le Backtester pour valoriser les positions) ; les autres colonnes
    portent une information corrélée au mouvement suivant pour que le modèle ait
    quelque chose à apprendre.
    """
    sets = []
    for i, close in enumerate(closes):
        previous = closes[i - 1] if i > 0 else close
        momentum = (close - previous) / previous
        sets.append(
            FeatureSet(
                symbol=SYMBOL,
                timeframe=TimeFrame.M1,
                timestamp=ORIGIN + timedelta(minutes=i),
                features={
                    "close_price": close,
                    "return_1d": momentum,
                    "ema_10": close * 0.999,
                    "rsi_14": 50.0 + momentum * 1000.0,
                    "atr_14": abs(momentum) * close,
                },
            )
        )
    return sets


def _trend(start: float, step_pct: float, n: int) -> List[float]:
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1.0 + step_pct))
    return closes


class TestSupervisedLabel:
    def test_label_is_the_next_bar_return(self) -> None:
        closes = [100.0, 101.0, 103.02]
        dataset = DatasetBuilder().build_supervised(_feature_sets(closes))

        # 3 barres -> 2 lignes étiquetées : la dernière n'a pas de successeur.
        assert len(dataset) == 2
        assert dataset.raw_data[0][TARGET_COLUMN] == pytest.approx(0.01)
        assert dataset.raw_data[1][TARGET_COLUMN] == pytest.approx(0.02)

    def test_label_is_absent_from_inference_dataset(self) -> None:
        """L'inférence ne fabrique pas de label : la barre suivante n'existe pas."""
        dataset = DatasetBuilder().build_from_features(_feature_sets([100.0, 101.0]))

        assert len(dataset) == 2
        assert TARGET_COLUMN not in dataset.raw_data[0]

    def test_missing_price_feature_is_rejected(self) -> None:
        naked = [
            FeatureSet(
                symbol=SYMBOL,
                timeframe=TimeFrame.M1,
                timestamp=ORIGIN,
                features={"rsi_14": 50.0},
            )
        ]
        with pytest.raises(ValueError, match="close_price"):
            DatasetBuilder().build_supervised(naked)


class TestTargetLeakage:
    def test_target_column_never_enters_the_feature_matrix(self) -> None:
        """Fuite parfaite si la cible sert de feature : le modèle apprend l'identité."""
        dataset = DatasetBuilder().build_supervised(_feature_sets(_trend(100.0, 0.002, 80)))

        matrix = _feature_matrix(dataset)

        assert TARGET_COLUMN not in matrix.columns
        # Le niveau de prix est lui aussi exclu : un arbre ne sait pas extrapoler
        # hors de la plage vue à l'entraînement, un split sur le prix mémorise
        # une période du calendrier. Seules les features dérivées survivent.
        assert "close_price" not in matrix.columns
        assert "rsi_14" in matrix.columns

    def test_identifiers_never_enter_the_feature_matrix(self) -> None:
        dataset = DatasetBuilder().build_supervised(_feature_sets(_trend(100.0, 0.002, 80)))

        matrix = _feature_matrix(dataset)

        for identifier in ("symbol", "timestamp", "timeframe"):
            assert identifier not in matrix.columns


class TestRealTraining:
    def test_training_reports_measured_metrics(self) -> None:
        dataset = DatasetBuilder().build_supervised(_feature_sets(_trend(100.0, 0.002, 200)))
        model = ModelFactory.create_model("lightgbm", n_estimators=30, verbose=-1)

        report = QlibTrainer().train(model, dataset)

        assert report["status"] == "success"
        assert report["samples"] == len(dataset)
        # Métriques réellement calculées, pas une constante : un RMSE négatif ou
        # une accuracy hors [0, 1] signalerait un rapport fabriqué.
        assert report["metrics"]["rmse"] >= 0.0
        assert report["metrics"]["mae"] >= 0.0
        assert 0.0 <= report["metrics"]["directional_accuracy"] <= 1.0
        assert report["training_time_seconds"] > 0.0

    def test_too_few_rows_fails_loudly(self) -> None:
        """20 barres ne suffisent pas : mieux vaut refuser que livrer un modèle creux."""
        dataset = DatasetBuilder().build_supervised(_feature_sets(_trend(100.0, 0.002, 20)))
        model = ModelFactory.create_model("lightgbm")

        with pytest.raises(ValueError, match="trop petit"):
            model.fit(dataset)

    def test_prediction_before_training_is_refused(self) -> None:
        model = ModelFactory.create_model("lightgbm")
        dataset = DatasetBuilder().build_from_features(_feature_sets([100.0, 101.0]))

        with pytest.raises(RuntimeError, match="trained"):
            model.predict(dataset)

    def test_inference_on_missing_columns_is_refused(self) -> None:
        """Un FeatureStore amputé doit échouer, pas prédire sur des colonnes absentes."""
        model = ModelFactory.create_model("lightgbm", n_estimators=20, verbose=-1)
        model.fit(DatasetBuilder().build_supervised(_feature_sets(_trend(100.0, 0.002, 80))))

        amputated = [
            FeatureSet(
                symbol=SYMBOL,
                timeframe=TimeFrame.M1,
                timestamp=ORIGIN,
                features={"close_price": 100.0, "rsi_14": 50.0},
            )
        ]
        with pytest.raises(ValueError, match="absentes"):
            model.predict(DatasetBuilder().build_from_features(amputated))

    def test_unsupported_model_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            ModelFactory.create_model("transformer")


class TestStrategyWiring:
    def _trained_strategy(self, closes: List[float], **kwargs: float) -> MLStrategy:
        model = ModelFactory.create_model("lightgbm", n_estimators=40, verbose=-1)
        model.fit(DatasetBuilder().build_supervised(_feature_sets(closes)))
        return MLStrategy(predictor=QlibPredictor(model), **kwargs)

    def test_uptrend_model_goes_long(self) -> None:
        closes = _trend(100.0, 0.002, 200)
        strategy = self._trained_strategy(closes)

        signals = strategy.generate_signals(_feature_sets(closes)[-1])

        assert len(signals) == 1
        assert signals[0].direction == 1
        assert signals[0].symbol == SYMBOL
        assert 0.0 < signals[0].strength <= 1.0

    def test_downtrend_model_goes_short(self) -> None:
        closes = _trend(100.0, -0.002, 200)
        strategy = self._trained_strategy(closes)

        signals = strategy.generate_signals(_feature_sets(closes)[-1])

        assert len(signals) == 1
        assert signals[0].direction == -1

    def test_prediction_inside_the_dead_zone_emits_nothing(self) -> None:
        """Sous le seuil, le rendement attendu ne couvre pas le coût : pas d'ordre."""
        closes = _trend(100.0, 0.002, 200)
        strategy = self._trained_strategy(closes, buy_threshold=10.0, sell_threshold=-10.0)

        assert strategy.generate_signals(_feature_sets(closes)[-1]) == []

    def test_inverted_thresholds_are_rejected(self) -> None:
        model = ModelFactory.create_model("lightgbm")
        with pytest.raises(ValueError, match="sell_threshold"):
            MLStrategy(
                predictor=QlibPredictor(model),
                buy_threshold=-0.001,
                sell_threshold=0.001,
            )
