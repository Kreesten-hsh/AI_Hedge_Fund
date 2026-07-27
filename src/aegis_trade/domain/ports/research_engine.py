from abc import ABC, abstractmethod
from typing import List
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.research import AlphaResearchResult, ResearchMetadata

class IResearchEngine(ABC):
    """
    Port for the Alpha Research Engine.
    Implementations of this interface evaluate the predictive power of features
    without leaking Machine Learning frameworks or Array libraries into the domain.
    """

    @abstractmethod
    def evaluate(self, features: List[FeatureSet], metadata: ResearchMetadata) -> AlphaResearchResult:
        """
        Evaluates a time series of FeatureSets against forward returns.
        
        Args:
            features: Chronological list of FeatureSets containing technical indicators and price data.
            metadata: Contextual data containing the forward_returns_lag and symbol context.
            
        Returns:
            AlphaResearchResult: Comprehensive evaluation report with IC metrics, scores, and rankings.
        """
        pass
