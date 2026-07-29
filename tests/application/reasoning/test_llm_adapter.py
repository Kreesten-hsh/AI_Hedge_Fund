import pytest
from aegis_trade.domain.reasoning import ClusterData
from aegis_trade.application.reasoning.llm_adapter import MockReasoner

def test_mock_reasoner():
    reasoner = MockReasoner()
    
    cluster_success = ClusterData(
        cluster_id=1,
        size=10,
        experience_ids=[],
        centroid_features={"f_0": 10.0, "f_1": 5.0},
        variance_features={"f_0": 1.0, "f_1": 0.25},
        is_success_cluster=True
    )
    
    hypothesis = reasoner.generate_hypothesis(cluster_success)
    assert "Success cluster found" in hypothesis
    assert "f_0: 10.00" in hypothesis
    assert "f_1: 5.00" in hypothesis
    
    cluster_failure = ClusterData(
        cluster_id=2,
        size=10,
        experience_ids=[],
        centroid_features={"f_0": -1.0},
        variance_features={"f_0": 0.1},
        is_success_cluster=False
    )
    
    hypothesis_fail = reasoner.generate_hypothesis(cluster_failure)
    assert "Failure cluster found" in hypothesis_fail
    assert "f_0: -1.00" in hypothesis_fail
