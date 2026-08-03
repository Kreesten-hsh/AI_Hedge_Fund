"""Adaptateur Qlib — chaîne réelle DatasetBuilder → LightGBM → Predictor → Stratégie.

Le mock LightGBM (sortie constante 0.55) a été supprimé : ces tests s'exécutent
sur un vrai `lightgbm.train`. Ils vérifient trois propriétés qu'un mock ne pouvait
pas porter : l'absence de fuite de la cible, l'échec bruyant sur données
insuffisantes ou désalignées, et la direction du signal issue d'un rendement
attendu (et non d'une probabilité).
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, List

import pytest

from aegis_trade.application.strategy.ml_strategy import MLStrategy
from aegis_trade.domain.core import AssetClass, Symbol, TimeFrame
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.engine.backtester import Backtester
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker
from aegis_trade.providers.qlib.dataset_builder import (
    TARGET_COLUMN,
    DatasetBuilder,
)
from aegis_trade.providers.qlib.model_factory import (
    IModel,
    LightGBMModel,
    ModelFactory,
    _feature_matrix,
)
from aegis_trade.providers.qlib.predictor import QlibPredictor
from aegis_trade.providers.qlib.trainer import QlibTrainer

SYMBOL = Symbol("CRASH1000", AssetClass.INDICES)
ORIGIN = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


class _ListFeed(IDataFeed):
    """Flux séquentiel sur des FeatureSets en mémoire."""

    def __init__(self, feature_sets: List[FeatureSet]) -> None:
        self._feature_sets = feature_sets

    def get_feature_stream(
        self, symbol: Symbol, timeframe: TimeFrame
    ) -> Iterator[FeatureSet]:
        return iter(self._feature_sets)


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


class TestHyperparameters:
    def test_defaults_are_kept_when_overriding_one_param(self) -> None:
        """Surcharger `n_estimators` ne doit pas effacer la graine.

        Un `kwargs or {defaults}` rendait tous les hyperparamètres morts dès le
        premier argument nommé — dont `random_state`, alors que l'artefact de
        validation enregistre `seed: 42` en affirmant la reproductibilité.
        """
        model = ModelFactory.create_model("lightgbm", n_estimators=42)

        assert isinstance(model, LightGBMModel)
        assert model.params["n_estimators"] == 42
        assert model.params["random_state"] == 42
        assert model.params["objective"] == "regression"
        assert model.params["learning_rate"] == 0.05

    def test_defaults_are_not_mutated_across_instances(self) -> None:
        """La surcharge d'une instance ne contamine pas la suivante."""
        ModelFactory.create_model("lightgbm", learning_rate=0.9)

        assert ModelFactory.create_model("lightgbm").params["learning_rate"] == 0.05


class TestPersistence:
    def test_save_then_load_predicts_identically(self, tmp_path: Path) -> None:
        """Un modèle rechargé doit prédire exactement comme l'original.

        C'est le chemin d'export du pipeline (`train_qlib_model.py`) : un booster
        rechargé qui dérive, ne serait-ce que d'un epsilon, invaliderait tout
        artefact de validation produit avant l'export.
        """
        closes = _trend(100.0, 0.002, 200)
        dataset = DatasetBuilder().build_supervised(_feature_sets(closes))
        model = ModelFactory.create_model("lightgbm", n_estimators=40, verbose=-1)
        model.fit(dataset)
        expected = model.predict(dataset)

        target = tmp_path / "models" / "lightgbm_test.txt"
        model.save(str(target))
        reloaded = LightGBMModel.load(str(target))

        assert target.exists()
        assert reloaded.predict(dataset) == pytest.approx(expected)

    def test_save_persists_the_feature_contract(self, tmp_path: Path) -> None:
        """Les noms de colonnes voyagent avec le booster, sinon désalignement muet."""
        dataset = DatasetBuilder().build_supervised(_feature_sets(_trend(100.0, 0.002, 200)))
        model = ModelFactory.create_model("lightgbm", n_estimators=20, verbose=-1)
        model.fit(dataset)

        target = tmp_path / "lightgbm_test.txt"
        model.save(str(target))
        sidecar = json.loads(target.with_suffix(".txt.meta.json").read_text(encoding="utf-8"))

        assert sidecar["feature_cols"] == LightGBMModel.load(str(target))._feature_cols
        assert TARGET_COLUMN not in sidecar["feature_cols"]
        assert "close_price" not in sidecar["feature_cols"]
        # La graine voyage aussi : un modèle rechargé et réentraîné doit repartir
        # des mêmes hyperparamètres que l'original.
        assert sidecar["params"]["random_state"] == 42

    def test_saving_an_untrained_model_is_refused(self, tmp_path: Path) -> None:
        model = ModelFactory.create_model("lightgbm")

        with pytest.raises(RuntimeError, match="trained"):
            model.save(str(tmp_path / "never_fitted.txt"))


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

    def test_prediction_inside_the_dead_zone_targets_flat(self) -> None:
        """Sous le seuil : exposition cible nulle, donc SORTIE — pas un silence.

        Rendre `[]` en zone morte laissait le Backtester porter indéfiniment la
        dernière position : il ne ferme que sur `direction == 0`. Mesuré sur le
        segment de test réel, 743 signaux short sans un seul long produisaient
        1 trade sur 1 500 barres. Un signal à 0 est une décision (« sortir »),
        l'absence de signal en est une autre (« ne rien changer »).
        """
        closes = _trend(100.0, 0.002, 200)
        strategy = self._trained_strategy(closes, buy_threshold=10.0, sell_threshold=-10.0)

        signals = strategy.generate_signals(_feature_sets(closes)[-1])

        assert len(signals) == 1
        assert signals[0].direction == 0
        # Aucune conviction directionnelle à porter : la force d'un ordre de
        # sortie n'a pas de sens, la quantité fermée est celle déjà détenue.
        assert signals[0].strength == 0.0

    def test_every_bar_carries_a_target_exposure(self) -> None:
        """Chaque barre porte exactement une cible : le silence n'est plus un état.

        Propriété structurelle : sans elle, le Backtester ne peut pas distinguer
        « le modèle ne sait pas » de « le modèle veut être plat ».
        """
        closes = _trend(100.0, 0.002, 200)
        strategy = self._trained_strategy(closes)

        for features in _feature_sets(closes)[-20:]:
            signals = strategy.generate_signals(features)
            assert len(signals) == 1
            assert signals[0].direction in (-1, 0, 1)

    def test_inverted_thresholds_are_rejected(self) -> None:
        model = ModelFactory.create_model("lightgbm")
        with pytest.raises(ValueError, match="sell_threshold"):
            MLStrategy(
                predictor=QlibPredictor(model),
                buy_threshold=-0.001,
                sell_threshold=0.001,
            )


class _ScriptedModel(IModel):
    """Modèle à prédictions scriptées, une par appel d'inférence.

    Le sujet des tests ci-dessous est la SORTIE, pas la qualité du modèle. Un vrai
    booster ne permet pas de commander la séquence conviction/zone morte dont on a
    besoin pour prouver qu'une position se ferme : on la scripte.
    """

    def __init__(self, returns: List[float]) -> None:
        self._returns = list(returns)
        self._calls = 0

    def fit(self, dataset: object) -> None:  # pragma: no cover - non appelé
        raise NotImplementedError

    def predict(self, dataset: object) -> List[float]:
        value = self._returns[min(self._calls, len(self._returns) - 1)]
        self._calls += 1
        return [value]


class TestExitLogicInBacktest:
    """La sortie se prouve dans un Backtester réel, pas sur la forme du signal.

    Un test qui n'observe que `direction == 0` n'aurait rien démontré : le défaut
    corrigé ici n'était pas la forme du signal, c'était l'absence de fermeture de
    position sur 1 500 barres.
    """

    def _run(self, expected_returns: List[float], closes: List[float]) -> Backtester:
        strategy = MLStrategy(predictor=QlibPredictor(_ScriptedModel(expected_returns)))
        backtester = Backtester(
            data_feed=_ListFeed(_feature_sets(closes)),
            strategy=strategy,
            # Friction nulle : on mesure ici le nombre de fermetures, pas le coût.
            broker=SimulatedBroker(commission_rate=0.0, slippage_bps=0.0),
        )
        backtester.run(SYMBOL, TimeFrame.M1)
        return backtester

    def test_dead_zone_closes_the_open_position(self) -> None:
        """Conviction puis zone morte : la position doit revenir à plat."""
        closes = _trend(100.0, 0.002, 6)
        # Barre 0 : achat. Barres 1+ : zone morte -> sortie.
        backtester = self._run([0.01] + [0.0] * 5, closes)

        fills = [t for t in backtester.trades_history if not t.get("rejected")]
        assert len(fills) == 2, "attendu : 1 entrée + 1 sortie"
        assert backtester.position == 0.0

    def test_a_held_position_is_not_rebought_every_bar(self) -> None:
        """Conviction constante : une seule entrée, pas de churn barre par barre."""
        closes = _trend(100.0, 0.002, 8)
        backtester = self._run([0.01] * 8, closes)

        fills = [t for t in backtester.trades_history if not t.get("rejected")]
        assert len(fills) == 1
        assert backtester.position > 0.0

    def test_alternating_conviction_produces_a_usable_trade_sample(self) -> None:
        """Le défaut de fond : 1 trade sur 1 500 barres, sous le plancher Monte-Carlo.

        Sans sortie, une conviction d'un seul signe ouvrait une position et la
        portait jusqu'au bout du segment. Avec l'exposition cible, chaque retour
        en zone morte referme, ce qui rend l'échantillon de trades exploitable.
        """
        closes = _trend(100.0, 0.002, 60)
        # Alternance conviction / zone morte : entrée, sortie, entrée, sortie...
        backtester = self._run([0.01, 0.0] * 30, closes)

        fills = [t for t in backtester.trades_history if not t.get("rejected")]
        assert len(fills) > 30, f"échantillon encore trop maigre : {len(fills)} trades"

    def test_flat_conviction_throughout_never_opens_a_position(self) -> None:
        """Zone morte de bout en bout : aucun ordre, et surtout aucun ordre de sortie."""
        closes = _trend(100.0, 0.002, 10)
        backtester = self._run([0.0] * 10, closes)

        assert backtester.trades_history == []
        assert backtester.position == 0.0


class _BrokenModel(IModel):
    """Modèle dont l'inférence échoue à partir d'une barre donnée."""

    def __init__(self, fail_from_call: int) -> None:
        self._fail_from_call = fail_from_call
        self._calls = 0

    def fit(self, dataset: object) -> None:  # pragma: no cover - non appelé
        raise NotImplementedError

    def predict(self, dataset: object) -> List[float]:
        self._calls += 1
        if self._calls > self._fail_from_call:
            raise RuntimeError("booster indisponible")
        return [0.01]


class _EmptyPredictionModel(IModel):
    """Modèle qui rend une liste vide : aucune ligne prédite."""

    def fit(self, dataset: object) -> None:  # pragma: no cover - non appelé
        raise NotImplementedError

    def predict(self, dataset: object) -> List[float]:
        return []


class TestInferenceFailureIsNotAnExitOrder:
    """Une panne d'inférence ne doit jamais valoir ordre de liquidation.

    Distinction que l'exposition cible rend critique : maintenant que `0` veut
    dire « sortir », confondre « je ne sais pas » et « je veux être plat »
    liquiderait le portefeuille sur une simple erreur technique.
    """

    def test_failed_inference_emits_no_target_at_all(self) -> None:
        strategy = MLStrategy(predictor=QlibPredictor(_BrokenModel(fail_from_call=0)))

        assert strategy.generate_signals(_feature_sets([100.0])[0]) == []

    def test_empty_prediction_emits_no_target_at_all(self) -> None:
        strategy = MLStrategy(predictor=QlibPredictor(_EmptyPredictionModel()))

        assert strategy.generate_signals(_feature_sets([100.0])[0]) == []

    def test_a_position_survives_an_inference_outage(self) -> None:
        """La position ouverte avant la panne est conservée, pas fermée."""
        closes = _trend(100.0, 0.002, 6)
        strategy = MLStrategy(predictor=QlibPredictor(_BrokenModel(fail_from_call=1)))
        backtester = Backtester(
            data_feed=_ListFeed(_feature_sets(closes)),
            strategy=strategy,
            broker=SimulatedBroker(commission_rate=0.0, slippage_bps=0.0),
        )
        backtester.run(SYMBOL, TimeFrame.M1)

        fills = [t for t in backtester.trades_history if not t.get("rejected")]
        assert len(fills) == 1, "l'entrée seule : la panne ne doit rien fermer"
        assert backtester.position > 0.0

    def test_non_positive_strength_scale_is_rejected(self) -> None:
        model = ModelFactory.create_model("lightgbm")
        with pytest.raises(ValueError, match="strength_scale"):
            MLStrategy(predictor=QlibPredictor(model), strength_scale=0.0)
