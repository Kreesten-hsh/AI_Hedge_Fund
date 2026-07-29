from typing import Optional, Dict
import json

from aegis_trade.domain.reasoning import (
    ILLMReasoner,
    ClusterData,
    Knowledge,
    AvoidPattern,
    PreferredPattern,
    KnowledgeScore,
    KnowledgeType
)
from aegis_trade.engine.reasoning_events import KnowledgeGeneratedEvent

class KnowledgeGenerator:
    """
    Generates Knowledge entities based on clusters using the LLM adapter.
    """
    def __init__(self, reasoner: ILLMReasoner):
        self.reasoner = reasoner

    def generate_from_cluster(self, cluster: ClusterData) -> Optional[Knowledge]:
        """
        Takes a cluster of experiences and generates a hypothesis using the LLM.
        """
        # Call the LLM to get a description
        hypothesis_description = self.reasoner.generate_hypothesis(cluster)
        
        # Initial score based purely on the cluster size
        # True validation is done by the KnowledgeValidator later
        initial_score = KnowledgeScore(
            confidence=0.0,  # Needs validation
            support=cluster.size,
            frequency=0.0,
            stability=0.0,
            recency=1.0  # Freshly generated
        )
        
        # Create an AvoidPattern if it's a failure cluster, PreferredPattern if success
        if cluster.is_success_cluster:
            knowledge = PreferredPattern(
                description=hypothesis_description,
                features_conditions=self._extract_conditions_from_cluster(cluster),
                score=initial_score,
                supporting_experience_ids=cluster.experience_ids
            )
        else:
            knowledge = AvoidPattern(
                description=hypothesis_description,
                features_conditions=self._extract_conditions_from_cluster(cluster),
                score=initial_score,
                supporting_experience_ids=cluster.experience_ids
            )
            
        return knowledge
        
    def _extract_conditions_from_cluster(self, cluster: ClusterData) -> Dict[str, Dict[str, float]]:
        """
        Basic condition extraction based on cluster centroid and variance.
        """
        conditions = {}
        for feature_name, centroid_val in cluster.centroid_features.items():
            variance = cluster.variance_features.get(feature_name, 0)
            # Create a basic min/max bound (e.g. 1 standard deviation)
            std_dev = max(variance ** 0.5, 0.001)
            conditions[feature_name] = {
                "min": centroid_val - (std_dev * 2),
                "max": centroid_val + (std_dev * 2)
            }
        return conditions

class KnowledgeValidator:
    """
    Validates hypotheses against statistical truth.
    """
    def __init__(self, min_support: int = 10, min_confidence: float = 0.6):
        self.min_support = min_support
        self.min_confidence = min_confidence

    def validate(self, knowledge: Knowledge, total_matching_experiences: int, total_matching_successes: int) -> bool:
        """
        Validates if the knowledge statistically holds up.
        """
        if total_matching_experiences < self.min_support:
            return False
            
        if knowledge.type == KnowledgeType.PREFERRED_PATTERN:
            confidence = total_matching_successes / total_matching_experiences
        elif knowledge.type == KnowledgeType.AVOID_PATTERN:
            confidence = (total_matching_experiences - total_matching_successes) / total_matching_experiences
        else:
            # For general observations, confidence might be calculated differently
            confidence = 1.0 
            
        if confidence < self.min_confidence:
            return False
            
        # Update score
        knowledge.score.confidence = confidence
        knowledge.score.support = total_matching_experiences
        
        return True
