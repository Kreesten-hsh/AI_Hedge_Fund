from typing import List, Dict, Any, Tuple
import numpy as np

from aegis_trade.domain.memory import Experience
from aegis_trade.domain.reasoning import ClusterData

class ExperienceAnalyzer:
    """
    Analyzes specific aspects of raw experiences (e.g., PnL distribution, duration).
    """
    
    def analyze_pnl_distribution(self, experiences: List[Experience]) -> Dict[str, float]:
        if not experiences:
            return {"mean": 0.0, "median": 0.0, "std_dev": 0.0, "min": 0.0, "max": 0.0}
            
        pnls = [float(exp.pnl) for exp in experiences]
        return {
            "mean": float(np.mean(pnls)),
            "median": float(np.median(pnls)),
            "std_dev": float(np.std(pnls)),
            "min": float(np.min(pnls)),
            "max": float(np.max(pnls))
        }
        
    def analyze_duration(self, experiences: List[Experience]) -> Dict[str, float]:
        if not experiences:
            return {"mean": 0.0, "median": 0.0, "std_dev": 0.0, "min": 0.0, "max": 0.0}
            
        durations = [float(exp.duration_seconds) for exp in experiences]
        return {
            "mean": float(np.mean(durations)),
            "median": float(np.median(durations)),
            "std_dev": float(np.std(durations)),
            "min": float(np.min(durations)),
            "max": float(np.max(durations))
        }

class SimilarityAnalyzer:
    """
    Analyzes how similar new market conditions are to known patterns.
    """
    
    def calculate_distance(self, current_features: Dict[str, float], cluster: ClusterData) -> float:
        """
        Calculates the Euclidean distance between current features and a cluster's centroid.
        """
        # We need to ensure we compare the same features in the same order
        # For simplicity in this implementation, we assume keys match and sort them
        distance = 0.0
        
        # Sort keys to ensure deterministic ordering
        feature_keys = sorted(current_features.keys())
        for key in feature_keys:
            current_val = current_features.get(key, 0.0)
            centroid_val = cluster.centroid_features.get(key, 0.0)
            
            # Simple squared difference
            distance += (current_val - centroid_val) ** 2
            
        return float(np.sqrt(distance))
        
    def is_within_bounds(self, current_features: Dict[str, float], cluster: ClusterData, max_std_dev: float = 2.0) -> bool:
        """
        Checks if current features fall within the N standard deviations of the cluster.
        """
        feature_keys = sorted(current_features.keys())
        for key in feature_keys:
            current_val = current_features.get(key, 0.0)
            centroid_val = cluster.centroid_features.get(key, 0.0)
            variance = cluster.variance_features.get(key, 0.0)
            
            std_dev = max(np.sqrt(variance), 0.001)
            
            if abs(current_val - centroid_val) > (std_dev * max_std_dev):
                return False
                
        return True
