import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Tuple

import numpy as np
import pandas as pd

from aegis_trade.providers.qlib.dataset_builder import QlibDataset, TARGET_COLUMN

logger = logging.getLogger(__name__)


class IModel(ABC):
    """Interface générique pour un modèle ML."""

    @abstractmethod
    def fit(self, dataset: QlibDataset) -> None:
        """Entraîne le modèle sur le dataset."""
        pass

    @abstractmethod
    def predict(self, dataset: QlibDataset) -> List[float]:
        """Génère des prédictions à partir du dataset."""
        pass


# Colonnes exclues de l'apprentissage : identifiants, cible et niveau de prix.
#
# `close_price` est exclu volontairement : un arbre de décision ne sait pas
# extrapoler hors de la plage vue à l'entraînement, et CRASH1000 dérive. Un split
# sur le niveau de prix revient à mémoriser une période du calendrier, pas à
# apprendre le marché — le modèle serait inutilisable dès que le prix sort de la
# plage d'entraînement. Le prix reste indispensable au dataset : il sert à
# construire le label forward et à valoriser les positions dans le Backtester.
#
# Le reste du FeatureStore (return_*, ema_*, rsi, macd, atr, bb_*, ...) est
# consommé tel quel : Qlib ne calcule jamais d'indicateur technique, il consomme
# des features pré-calculées (règle actée dans CLAUDE.md).
_NON_FEATURE_COLUMNS = frozenset(
    {"symbol", "timestamp", "timeframe", "target", "close_price", TARGET_COLUMN}
)


def _feature_matrix(dataset: QlibDataset) -> pd.DataFrame:
    """Tableau dense des features numériques, indexé par timestamp."""
    df = pd.DataFrame(dataset.raw_data)
    if df.empty:
        return pd.DataFrame()

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    # La cible du dataset est exclue par son nom exact, en plus de la constante :
    # laisser la colonne cible dans X serait une fuite parfaite (le modèle
    # apprendrait l'identité et afficherait un RMSE irréel).
    excluded = _NON_FEATURE_COLUMNS | {dataset.target_col}
    drop_cols = [c for c in excluded if c in df.columns]
    feature_cols = [c for c in df.columns if c not in drop_cols]
    if not feature_cols:
        raise ValueError("QlibDataset ne contient aucune colonne de features.")

    X = df[feature_cols].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)

    # Colonnes intégralement NaN : aucune information, et elles videraient le
    # filtre _drop_na_rows. C'est le cas de rel_volume et vwap sur les
    # synthétiques Deriv, dont le volume est nul : les jeter n'appauvrit rien,
    # et elles disparaissent aussi du contrat de features du modèle (elles ne
    # sont jamais sélectionnées à l'inférence non plus).
    all_nan = [c for c in X.columns if X[c].isna().all()]
    if all_nan:
        logger.info("Colonnes sans information retirées : %s", all_nan)
        X = X.drop(columns=all_nan)

    return X


def _target_series(dataset: QlibDataset) -> pd.Series:
    """Série de la variable cible, alignée sur _feature_matrix."""
    if not dataset.raw_data:
        raise ValueError("QlibDataset vide : aucune cible à extraire.")
    if dataset.target_col not in dataset.raw_data[0]:
        raise ValueError(f"Colonne cible '{dataset.target_col}' absente du dataset.")
    df = pd.DataFrame(dataset.raw_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return pd.to_numeric(df[dataset.target_col], errors="coerce").astype(float)


def _drop_na_rows(X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
    """Retire les lignes dont une feature ou la cible est manquante.

    Les premières barres d'un FeatureStore ont des fenêtres roulantes incomplètes
    (NaN). Les imputer introduirait une valeur que le marché n'a jamais portée ;
    les jeter est le seul choix qui ne fabrique pas de donnée.
    """
    valid = y.notna()
    for col in X.columns:
        valid &= X[col].notna()
    return X.loc[valid], y.loc[valid]


class LightGBMModel(IModel):
    """
    Vrai modèle LightGBM entraîné sur le FeatureStore.

    Contournement LightGBM-direct : `qlib.init()` est inatteignable tant que
    `mlflow 1.27.0` est installé (qlib 0.9.7 importe `mlflow.exceptions`, absent
    de cette distribution). L'entraînement passe donc par `lightgbm` directement,
    sur les features du FeatureStore. Contournement temporaire : la note de sortie
    est écrite dans `GITHUB_INTEGRATION_GUIDE.md` ; le vrai `qlib.init()` sera
    réactivé au Lot 5 après upgrade de mlflow.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.params = kwargs or {
            "objective": "regression",
            "metric": "rmse",
            "n_estimators": 300,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_child_samples": 20,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "verbose": -1,
        }
        self._model: Any = None
        self._feature_cols: List[str] = []

    def fit(self, dataset: QlibDataset) -> None:
        import lightgbm as lgb  # import tardif : dépendance optionnelle

        X = _feature_matrix(dataset)
        y = _target_series(dataset)
        X, y = _drop_na_rows(X, y)

        if len(X) < 50:
            raise ValueError(
                f"Dataset trop petit pour l'entraînement ({len(X)} lignes valides < 50)."
            )

        self._feature_cols = list(X.columns)
        # Dataset LightGBM sans construction d'histogramme : le FeatureStore est
        # déjà numérique et propre, on économise la passe de validation interne.
        lgb_train = lgb.Dataset(X, label=y, free_raw_data=True)
        self._model = lgb.train(
            self.params,
            lgb_train,
            num_boost_round=int(self.params.get("n_estimators", 300)),
        )
        logger.info("LightGBM entraîné sur %d lignes, %d features.", len(X), len(self._feature_cols))

    def predict(self, dataset: QlibDataset) -> List[float]:
        if self._model is None:
            raise RuntimeError("Model must be trained before predicting.")
        X = _feature_matrix(dataset)
        # Alignement strict : un FeatureStore qui n'expose pas les mêmes colonnes
        # que l'entraînement doit échouer bruyamment, pas prédire sur des colonnes
        # manquantes remplies à zéro.
        missing = [c for c in self._feature_cols if c not in X.columns]
        if missing:
            raise ValueError(
                f"Colonnes d'entraînement absentes à l'inférence : {missing}."
            )
        X = X[self._feature_cols]
        X = X.replace([np.inf, -np.inf], np.nan)
        preds = self._model.predict(X)
        # Les NaN en entrée donnent des prédictions NaN : l'inférence ne renvoie
        # jamais un NaN silencieux, elle lève pour que l'appelant décide.
        if np.isnan(preds).any():
            raise ValueError("Prédictions NaN (features d'entrée invalides).")
        return [float(p) for p in preds]


    def save(self, path: str) -> None:
        """Persiste le booster et le contrat de features.

        Deux fichiers, tous deux lisibles par un humain : le booster au format
        texte natif LightGBM, et un sidecar JSON avec les paramètres et les noms
        de colonnes. Pas de pickle : le fichier rechargé par `load` doit pouvoir
        être inspecté, et un artefact produit par la pipeline locale ne doit pas
        dépendre d'un format d'exécution arbitraire.

        Les noms de colonnes voyagent avec le booster : les recharger séparément
        exposerait à un désalignement silencieux entre l'ordre des features à
        l'entraînement et à l'inférence.
        """
        if self._model is None:
            raise RuntimeError("Model must be trained before saving.")

        booster_path = Path(path)
        booster_path.parent.mkdir(parents=True, exist_ok=True)
        self._model.save_model(str(booster_path))

        sidecar = {
            "params": self.params,
            "feature_cols": self._feature_cols,
        }
        with booster_path.with_suffix(booster_path.suffix + ".meta.json").open(
            "w", encoding="utf-8"
        ) as handle:
            json.dump(sidecar, handle, indent=2)
        logger.info("Modèle sauvegardé : %s (+ .meta.json)", booster_path)

    @classmethod
    def load(cls, path: str) -> "LightGBMModel":
        """Recharge un modèle entraîné depuis le disque (booster + sidecar JSON)."""
        import lightgbm as lgb  # import tardif : dépendance optionnelle

        booster_path = Path(path)
        meta_path = booster_path.with_suffix(booster_path.suffix + ".meta.json")
        with meta_path.open("r", encoding="utf-8") as handle:
            sidecar = json.load(handle)

        model = cls(**sidecar["params"])
        model._feature_cols = list(sidecar["feature_cols"])
        model._model = lgb.Booster(model_file=str(booster_path))
        return model


class ModelFactory:
    """Usine pour instancier les algorithmes de Machine Learning pris en charge."""

    @staticmethod
    def create_model(model_name: str, **kwargs: Any) -> IModel:
        if model_name.lower() == "lightgbm":
            return LightGBMModel(**kwargs)
        else:
            raise ValueError(f"Model {model_name} is not supported.")
