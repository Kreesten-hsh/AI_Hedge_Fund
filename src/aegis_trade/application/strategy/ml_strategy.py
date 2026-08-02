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

    Le modèle prédit un RENDEMENT ATTENDU (cible `forward_return_1`), pas une
    probabilité. Les seuils sont donc exprimés en rendement : sur du M1 synthétique
    un mouvement d'une barre se compte en 1e-4, un seuil de 0.5 ne se déclencherait
    jamais. Les anciens seuils 0.52/0.48 étaient calibrés sur la sortie constante
    0.55 du mock LightGBM supprimé au Lot 4.
    """

    def __init__(
        self,
        predictor: QlibPredictor,
        buy_threshold: float = 0.0002,
        sell_threshold: float = -0.0002,
        strength_scale: float = 0.001,
    ):
        """
        :param predictor: L'instance de prédiction encapsulant le modèle Qlib (ou autre).
        :param buy_threshold: Rendement attendu au-dessus duquel on ACHÈTE.
        :param sell_threshold: Rendement attendu en-dessous duquel on VEND.
        :param strength_scale: Rendement correspondant à une conviction de 1.0.
        """
        if sell_threshold >= buy_threshold:
            raise ValueError(
                "sell_threshold doit être strictement inférieur à buy_threshold "
                f"(reçu {sell_threshold} >= {buy_threshold})."
            )
        if strength_scale <= 0.0:
            raise ValueError("strength_scale doit être strictement positif.")

        self.predictor = predictor
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.strength_scale = strength_scale
        self.dataset_builder = DatasetBuilder()

    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        """
        1. Convertit le FeatureSet courant en un Dataset compréhensible par le Predictor.
        2. Invoque l'inférence.
        3. Convertit le rendement attendu en Signal (Direction 1, -1 ou 0).
        """
        # Construction d'un mini-dataset (1 ligne) pour l'inférence. Pas de label :
        # à la décision, la barre suivante n'existe pas encore.
        dataset = self.dataset_builder.build_from_features([features])

        try:
            predictions = self.predictor.predict(dataset)

            if not predictions:
                return []

            expected_return = predictions[0]

            direction = 0
            if expected_return >= self.buy_threshold:
                direction = 1
            elif expected_return <= self.sell_threshold:
                direction = -1

            if direction != 0:
                # Signal.strength est un score de conviction borné [0, 1] : un
                # rendement attendu de `strength_scale` sature la conviction.
                strength = min(abs(expected_return) / self.strength_scale, 1.0)
                return [Signal(
                    symbol=features.symbol,
                    direction=direction,
                    strength=strength,
                    timestamp=features.timestamp
                )]
            return []

        except Exception as e:
            logger.error(f"MLStrategy inference failed on symbol {features.symbol} : {e}")
            return []
