from typing import List
import logging

from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.features import FeatureSet
from aegis_trade.providers.qlib.predictor import QlibPredictor
from aegis_trade.providers.qlib.dataset_builder import DatasetBuilder

logger = logging.getLogger(__name__)

class MLStrategy(IStrategy):
    """
    Stratégie qui utilise un modèle Machine Learning (via QlibPredictor) 
    pour générer ses signaux d'achats ou de ventes.
    Agit comme un pont entre le monde ML et le monde Trading d'Aegis Quant OS.
    """
    def __init__(self, predictor: QlibPredictor, buy_threshold: float = 0.52, sell_threshold: float = 0.48):
        """
        :param predictor: L'instance de prédiction encapsulant le modèle Qlib (ou autre).
        :param buy_threshold: Seuil au-dessus duquel le signal de prédiction déclenche un ACHAT.
        :param sell_threshold: Seuil en-dessous duquel le signal de prédiction déclenche une VENTE.
        """
        self.predictor = predictor
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.dataset_builder = DatasetBuilder()
        
    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        """
        1. Convertit le FeatureSet courant en un Dataset compréhensible par le Predictor.
        2. Invoque l'inférence.
        3. Convertit le score quantitatif en Signal (Direction 1, -1 ou 0).
        """
        # Construction d'un mini-dataset (1 ligne) pour l'inférence
        dataset = self.dataset_builder.build_from_features([features])
        
        try:
            predictions = self.predictor.predict(dataset)
            
            if not predictions:
                return []
                
            score = predictions[0]
            
            direction = 0
            if score >= self.buy_threshold:
                direction = 1
            elif score <= self.sell_threshold:
                direction = -1
                
            if direction != 0:
                return [Signal(
                    symbol=features.symbol,
                    direction=direction,
                    strength=abs(score - 0.5) * 2.0, # Normalisation basique
                    timestamp=features.timestamp
                )]
            return []
            
        except Exception as e:
            logger.error(f"MLStrategy inference failed on symbol {features.symbol} : {e}")
            return []
