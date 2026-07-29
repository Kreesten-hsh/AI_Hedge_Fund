import pytest
from aegis_trade.domain.reasoning import ClusterData, KnowledgeType, AvoidPattern, PreferredPattern
from aegis_trade.application.reasoning.knowledge import KnowledgeGenerator, KnowledgeValidator
from aegis_trade.application.reasoning.llm_adapter import MockReasoner

def test_knowledge_generator():
    reasoner = MockReasoner()
    generator = KnowledgeGenerator(reasoner)
    
    cluster = ClusterData(
        cluster_id=1,
        size=10,
        experience_ids=["1", "2", "3"],
        centroid_features={"rsi": 85.0},
        variance_features={"rsi": 2.0},
        is_success_cluster=False
    )
    
    knowledge = generator.generate_from_cluster(cluster)
    
    assert isinstance(knowledge, AvoidPattern)
    assert knowledge.type == KnowledgeType.AVOID_PATTERN
    assert "Failure cluster found" in knowledge.description
    assert knowledge.score.support == 10
    
    assert "rsi" in knowledge.features_conditions
    assert knowledge.features_conditions["rsi"]["min"] < 85.0
    assert knowledge.features_conditions["rsi"]["max"] > 85.0

def test_knowledge_validator():
    validator = KnowledgeValidator(min_support=10, min_confidence=0.6)
    reasoner = MockReasoner()
    generator = KnowledgeGenerator(reasoner)
    
    cluster = ClusterData(
        cluster_id=1,
        size=20,
        experience_ids=[],
        centroid_features={"rsi": 85.0},
        variance_features={"rsi": 2.0},
        is_success_cluster=False
    )
    
    knowledge = generator.generate_from_cluster(cluster)
    
    # 15 failures out of 20 experiences matches the pattern -> confidence = 15/20 = 0.75 (>= 0.6)
    is_valid = validator.validate(knowledge, total_matching_experiences=20, total_matching_successes=5)
    
    assert is_valid
    assert knowledge.score.confidence == 0.75
    assert knowledge.score.support == 20
    
    # Less than min support
    is_valid_low_support = validator.validate(knowledge, total_matching_experiences=5, total_matching_successes=0)
    assert not is_valid_low_support
    
    # Low confidence
    # 5 failures out of 20 matches -> confidence = 5/20 = 0.25
    is_valid_low_conf = validator.validate(knowledge, total_matching_experiences=20, total_matching_successes=15)
    assert not is_valid_low_conf
