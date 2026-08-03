from abc import ABC, abstractmethod
from typing import Callable
import logging

from aegis_trade.domain.validation import ValidationCampaignResult
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.execution import IBroker
from aegis_trade.application.validation.config import ValidationConfig

logger = logging.getLogger(__name__)

class IValidator(ABC):
    """
    Interface commune pour tous les validateurs de stratégie (Walk-Forward, Monte Carlo, etc.)
    Chaque validateur est responsable d'exécuter un type spécifique de test de robustesse.
    """
    
    @abstractmethod
    def run(
        self, 
        strategy: IStrategy, 
        data_feed: IDataFeed, 
        broker_factory: Callable[[], IBroker],
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        """
        Exécute la campagne de validation.

        Args:
            strategy: La stratégie à évaluer.
            data_feed: Le flux de données.
            broker_factory: Fabrique sans argument produisant un broker neuf pour
                chaque simulation. Une fabrique (et non une classe) permet de
                passer un broker déjà paramétré en coûts, de sorte que la
                stratégie et l'exécution partagent le même modèle de coût.
            config: La configuration globale de validation.
            
        Returns:
            ValidationCampaignResult: Les résultats et le statut PASS/FAIL du test.
        """
        pass
