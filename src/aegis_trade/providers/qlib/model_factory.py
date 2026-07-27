from abc import ABC, abstractmethod
from typing import Dict, Any, List

class IModel(ABC):
    """Interface générique pour un modèle ML."""
    
    @abstractmethod
    def fit(self, dataset: Any) -> None:
        """Entraîne le modèle sur le dataset."""
        pass
        
    @abstractmethod
    def predict(self, dataset: Any) -> List[float]:
        """Génère des prédictions à partir du dataset."""
        pass

class LightGBMModelMock(IModel):
    """
    Mock d'un modèle LightGBM pour la preuve de concept (PoC).
    Dans l'intégration finale, ceci encapsulera le vrai LGBMClassifier/Regressor ou le modèle Qlib.
    """
    def __init__(self, **kwargs):
        self.params = kwargs
        self._is_trained = False
        
    def fit(self, dataset: Any) -> None:
        """Simule l'entraînement."""
        self._is_trained = True
        
    def predict(self, dataset: Any) -> List[float]:
        """Simule la prédiction. Renvoie des scores fictifs."""
        if not self._is_trained:
            raise RuntimeError("Model must be trained before predicting.")
        # Simule un score prédictif pour chaque ligne du dataset
        return [0.55 for _ in range(len(dataset))]

class ModelFactory:
    """
    Usine pour instancier les algorithmes de Machine Learning pris en charge.
    """
    @staticmethod
    def create_model(model_name: str, **kwargs) -> IModel:
        if model_name.lower() == "lightgbm":
            return LightGBMModelMock(**kwargs)
        # elif model_name.lower() == "xgboost": ...
        else:
            raise ValueError(f"Model {model_name} is not supported.")
