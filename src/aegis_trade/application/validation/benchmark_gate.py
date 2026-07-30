import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class BenchmarkGate:
    """
    Enforces strict static performance thresholds on backtest metrics.
    Rejects any model that fails to meet baseline requirements (e.g., Win Rate, Sortino).
    """
    def __init__(self, min_win_rate: float = 0.55, min_sortino: float = 1.2):
        self.min_win_rate = min_win_rate
        self.min_sortino = min_sortino

    def evaluate(self, metrics: Dict[str, float]) -> Tuple[bool, str]:
        """
        Evaluates a dictionary of performance metrics against the thresholds.
        
        Args:
            metrics: Dict containing at minimum 'win_rate' and 'sortino_ratio'
            
        Returns:
            Tuple[bool, str]: (Passed, Reason)
        """
        win_rate = metrics.get("win_rate", 0.0)
        sortino = metrics.get("sortino_ratio", 0.0)
        
        reasons = []
        if win_rate < self.min_win_rate:
            reasons.append(f"Win Rate ({win_rate:.2f}) below threshold ({self.min_win_rate:.2f})")
        if sortino < self.min_sortino:
            reasons.append(f"Sortino Ratio ({sortino:.2f}) below threshold ({self.min_sortino:.2f})")
            
        if reasons:
            reason_str = " | ".join(reasons)
            logger.warning(f"BenchmarkGate Rejected: {reason_str}")
            return False, reason_str
            
        return True, "Passed all benchmark thresholds"
