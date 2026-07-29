import numpy as np
from typing import List, Dict, Any, Optional
from collections import defaultdict
from sklearn.cluster import DBSCAN, HDBSCAN

from aegis_trade.domain.reasoning import IClusterEngine, ClusterData

class DBSCANClusterEngine(IClusterEngine):
    """
    Implements DBSCAN for clustering experiences.
    Does not force all points into clusters (noise is allowed).
    """
    
    def find_clusters(self, vectors: List[List[float]], metadata: List[Dict[str, Any]], epsilon: float = 0.5, min_samples: int = 5) -> List[ClusterData]:
        if not vectors:
            return []
            
        X = np.array(vectors)
        dbscan = DBSCAN(eps=epsilon, min_samples=min_samples, metric='euclidean')
        labels = dbscan.fit_predict(X)
        
        return self._process_labels(X, labels, metadata)

    def _process_labels(self, X: np.ndarray, labels: np.ndarray, metadata: List[Dict[str, Any]]) -> List[ClusterData]:
        clusters_map = defaultdict(list)
        
        for i, label in enumerate(labels):
            if label != -1:  # -1 means noise in DBSCAN/HDBSCAN
                clusters_map[label].append(i)
                
        results = []
        for cluster_id, indices in clusters_map.items():
            cluster_vectors = X[indices]
            
            centroid = np.mean(cluster_vectors, axis=0)
            variance = np.var(cluster_vectors, axis=0)
            
            experience_ids = [metadata[i].get("id", str(i)) for i in indices]
            is_success_cluster = all(metadata[i].get("category") == "success" for i in indices)
            # Alternatively, we could define success if > 80% are successes
            
            # Simple metadata extraction for centroid features representation (using feature names if present in metadata)
            # In practice, features should be mapped back from the centroid vector
            centroid_features = {f"f_{j}": float(centroid[j]) for j in range(len(centroid))}
            variance_features = {f"f_{j}": float(variance[j]) for j in range(len(variance))}
            
            results.append(ClusterData(
                cluster_id=int(cluster_id),
                size=len(indices),
                experience_ids=experience_ids,
                centroid_features=centroid_features,
                variance_features=variance_features,
                is_success_cluster=is_success_cluster
            ))
            
        return results

class HDBSCANClusterEngine(DBSCANClusterEngine):
    """
    Implements HDBSCAN for clustering experiences with varying density.
    """
    
    def find_clusters(self, vectors: List[List[float]], metadata: List[Dict[str, Any]], epsilon: float = 0.5, min_samples: int = 5) -> List[ClusterData]:
        if not vectors:
            return []
            
        X = np.array(vectors)
        # HDBSCAN doesn't strictly need epsilon, min_samples is the key parameter
        hdbscan = HDBSCAN(min_cluster_size=min_samples, min_samples=min_samples)
        labels = hdbscan.fit_predict(X)
        
        return self._process_labels(X, labels, metadata)

class FailurePatternDiscovery:
    """
    Service to find patterns strictly in failure experiences.
    """
    def __init__(self, engine: IClusterEngine):
        self.engine = engine
        
    def discover(self, failure_vectors: List[List[float]], failure_metadata: List[Dict[str, Any]]) -> List[ClusterData]:
        return self.engine.find_clusters(failure_vectors, failure_metadata)

class SuccessPatternDiscovery:
    """
    Service to find patterns strictly in success experiences.
    """
    def __init__(self, engine: IClusterEngine):
        self.engine = engine
        
    def discover(self, success_vectors: List[List[float]], success_metadata: List[Dict[str, Any]]) -> List[ClusterData]:
        return self.engine.find_clusters(success_vectors, success_metadata)
