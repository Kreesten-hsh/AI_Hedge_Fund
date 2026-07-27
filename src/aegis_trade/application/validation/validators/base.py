from abc import ABC, abstractmethod
from typing import Type
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
        broker_factory: Type[IBroker], 
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        """
        Exécute la campagne de validation.
        
        Args:
            strategy: La stratégie à évaluer.
            data_feed: Le flux de données.
            broker_factory: La classe/factory pour instancier un broker neuf pour chaque simulation.
            config: La configuration globale de validation.
            
        Returns:
            ValidationCampaignResult: Les résultats et le statut PASS/FAIL du test.
        """
        pass
