import pytest
from aegis_trade.application.reasoning.clustering import DBSCANClusterEngine, HDBSCANClusterEngine, FailurePatternDiscovery

def test_dbscan_clustering():
    engine = DBSCANClusterEngine()
    
    # Create two distinct clusters
    # Cluster 1 (around 0)
    # Cluster 2 (around 10)
    vectors = [
        [0.1, 0.1],
        [0.2, 0.1],
        [0.1, 0.2],
        [0.2, 0.2],
        [0.15, 0.15],
        [0.1, 0.15], # 6 points
        
        [10.1, 10.1],
        [10.2, 10.1],
        [10.1, 10.2],
        [10.2, 10.2],
        [10.15, 10.15], # 5 points
        
        [50.0, 50.0] # 1 noise point
    ]
    
    metadata = [{"id": f"exp-{i}", "category": "failure"} for i in range(len(vectors))]
    
    # min_samples=3, eps=1.0
    clusters = engine.find_clusters(vectors, metadata, epsilon=1.0, min_samples=3)
    
    assert len(clusters) == 2
    
    sizes = [c.size for c in clusters]
    assert 5 in sizes
    assert 6 in sizes
    
def test_failure_discovery():
    engine = DBSCANClusterEngine()
    discovery = FailurePatternDiscovery(engine)
    
    vectors = [[0.0, 0.0], [0.1, 0.1], [0.0, 0.1], [0.1, 0.0], [0.05, 0.05], [0.0, 0.05]]
    metadata = [{"id": f"fail-{i}", "category": "failure"} for i in range(6)]
    
    clusters = discovery.discover(vectors, metadata)
    assert len(clusters) == 1
    assert clusters[0].size == 6
    assert not clusters[0].is_success_cluster
