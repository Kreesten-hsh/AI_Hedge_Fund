import logging
import time
from typing import Dict, Any

import numpy as np

from aegis_trade.providers.qlib.model_factory import IModel
from aegis_trade.providers.qlib.dataset_builder import QlibDataset

logger = logging.getLogger(__name__)

class QlibTrainer:
    """
    Anti-Corruption Layer : Encapsule le cycle de vie de l'entraînement ML.
    Appelle le `.fit()` du modèle et journalise les métriques et temps d'exécution.
    """

    def train(self, model: IModel, dataset: QlibDataset) -> Dict[str, Any]:
        """
        Déclenche l'entraînement sur un modèle vierge avec le dataset fourni.

        :return: Un dictionnaire de métadonnées et métriques d'entraînement.
        """
        logger.info("Starting model training pipeline.")
        start_time = time.time()

        # Un échec d'entraînement remonte à l'appelant. L'ancien `except`
        # renvoyait `status: failed` qu'aucun appelant ne lisait : le pipeline
        # continuait ensuite avec un modèle non entraîné.
        model.fit(dataset)
        execution_time = time.time() - start_time

        # Métriques réellement mesurées sur les données d'entraînement. Ce sont
        # des métriques d'AJUSTEMENT, pas une validation : le verdict GO/NO-GO
        # appartient aux 6 validateurs du Lot 4, jamais à ce rapport.
        preds = np.asarray(model.predict(dataset), dtype=float)
        actuals = np.asarray(
            [float(row[dataset.target_col]) for row in dataset.raw_data], dtype=float
        )
        n = min(len(preds), len(actuals))
        preds, actuals = preds[:n], actuals[:n]

        residuals = preds - actuals
        rmse = float(np.sqrt(np.mean(residuals**2)))
        mae = float(np.mean(np.abs(residuals)))
        # Part des barres où le SIGNE du rendement prédit est correct : c'est la
        # métrique la plus proche de ce que la stratégie exploite réellement.
        directional_accuracy = float(np.mean(np.sign(preds) == np.sign(actuals)))

        logger.info(
            "Training completed in %.2fs - RMSE=%.6g MAE=%.6g dir_acc=%.4f",
            execution_time, rmse, mae, directional_accuracy,
        )

        return {
            "status": "success",
            "training_time_seconds": execution_time,
            "samples": int(n),
            "metrics": {
                "rmse": rmse,
                "mae": mae,
                "directional_accuracy": directional_accuracy,
            },
        }
