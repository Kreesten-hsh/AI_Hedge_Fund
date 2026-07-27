from typing import List
import logging

from aegis_trade.providers.qlib.model_factory import IModel
from aegis_trade.providers.qlib.dataset_builder import QlibDataset

logger = logging.getLogger(__name__)

class QlibPredictor:
    """
    Anti-Corruption Layer : Encapsule l'inférence (predict) d'un modèle entraîné.
    Ne renvoie strictement que des valeurs quantitatives (scores, rendements espérés),
    jamais de signaux de trading métier (BUY/SELL).
    """
    
    def __init__(self, model: IModel):
        self.model = model
        
    def predict(self, dataset: QlibDataset) -> List[float]:
        """
        Exécute l'inférence sur un dataset de features.
        
        :param dataset: Le dataset construit depuis le FeatureStore.
        :return: Liste de scores de prédictions correspondants.
        """
        try:
            predictions = self.model.predict(dataset)
            return predictions
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise
