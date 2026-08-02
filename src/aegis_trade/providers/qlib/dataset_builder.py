import logging
from typing import Any, Dict, Iterable, List

import pandas as pd

from aegis_trade.domain.features import FeatureSet

logger = logging.getLogger(__name__)

# Nom de la cible. Distinct de `return_1d` du FeatureStore, qui est un
# `pct_change(1)` — donc un rendement PASSÉ, légitime comme feature. La cible
# est le rendement de la barre SUIVANTE : les confondre entraînerait le modèle
# à prédire une valeur qu'il reçoit déjà en entrée (fuite parfaite, score
# irréprochable en backtest et sans valeur en production).
TARGET_COLUMN = "forward_return_1"


class QlibDataset:
    """
    Encapsulation du format de données attendu par les modèles ML.
    (Normalement TSDatasetH dans Microsoft Qlib)
    """
    def __init__(self, data: List[Dict[str, Any]], target_col: str = TARGET_COLUMN):
        self._data = data
        self.target_col = target_col

    @property
    def raw_data(self) -> List[Dict[str, Any]]:
        return self._data

    def __len__(self) -> int:
        return len(self._data)


class DatasetBuilder:
    """
    Anti-Corruption Layer : Construit un Dataset Qlib depuis le Feature Store d'Aegis.
    Le Feature Store reste l'unique source de vérité. Aucune feature n'est calculée ici.
    """

    def __init__(self, target_feature: str = TARGET_COLUMN, price_key: str = "close_price"):
        """
        :param target_feature: Nom de la colonne cible (Y).
        :param price_key: Feature portant le prix de clôture, base du label forward.
            `close_price` est le nom déjà lu par le Backtester pour valoriser les
            positions : une seule clé de prix dans tout le pipeline.
        """
        self.target_feature = target_feature
        self.price_key = price_key

    def build_from_features(self, feature_sets: Iterable[FeatureSet]) -> QlibDataset:
        """
        Transforme un flux de FeatureSet en QlibDataset (format tabulaire).

        N'ajoute aucun label : utilisé pour l'inférence en ligne, où la barre
        suivante n'existe pas encore par définition.
        """
        logger.info(f"Building dataset from FeatureSets. Target: {self.target_feature}")

        data_rows = []
        for fset in feature_sets:
            row: Dict[str, Any] = {
                "symbol": fset.symbol,
                "timestamp": fset.timestamp.isoformat(),
                "timeframe": fset.timeframe.value
            }
            for feat_name, feat_val in fset.features.items():
                row[feat_name] = feat_val

            data_rows.append(row)

        dataset = QlibDataset(data=data_rows, target_col=self.target_feature)
        logger.info(f"Dataset built with {len(dataset)} rows.")
        return dataset

    def build_supervised(self, feature_sets: Iterable[FeatureSet]) -> QlibDataset:
        """
        Construit un dataset étiqueté pour l'entraînement.

        Le label est le rendement de la barre suivante (horizon 1 barre, décidé
        pour le scalping : un horizon de 5 barres est trop long face au style de
        trading visé). La dernière barre n'a pas de successeur : elle est retirée
        plutôt qu'étiquetée à zéro, qui serait un rendement inventé.
        """
        dataset = self.build_from_features(feature_sets)
        rows = dataset.raw_data
        if not rows:
            return dataset

        df = pd.DataFrame(rows)
        if self.price_key not in df.columns:
            raise ValueError(
                f"Feature de prix '{self.price_key}' absente : impossible de "
                f"construire le label {self.target_feature}."
            )

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp").reset_index(drop=True)

        price = pd.to_numeric(df[self.price_key], errors="coerce")
        # shift(-1) regarde la barre suivante : c'est la seule direction qui
        # produit une cible non observable au moment de la décision.
        df[self.target_feature] = price.shift(-1) / price - 1.0
        df = df.iloc[:-1]
        df = df[df[self.target_feature].notna()]

        df["timestamp"] = df["timestamp"].map(lambda ts: ts.isoformat())
        labelled = df.to_dict(orient="records")
        logger.info(
            "Supervised dataset: %d lignes étiquetées (%s).",
            len(labelled),
            self.target_feature,
        )
        return QlibDataset(data=labelled, target_col=self.target_feature)
