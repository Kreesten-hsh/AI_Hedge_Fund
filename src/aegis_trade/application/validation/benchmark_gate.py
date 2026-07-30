import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class BenchmarkGate:
    """
    Enforces strict static performance thresholds on backtest metrics.
    Rejects any model that fails to meet baseline requirements.
    Fails safely if a metric is missing.
    """
    def __init__(
        self, 
        min_win_rate: float = 0.85, 
        min_sortino: float = 2.0,
        min_sharpe: float = 1.5,
        max_drawdown: float = 0.05,
        max_recovery_factor_hours: float = 48.0,
        max_latency_ms: float = 20.0,
        max_slippage_pips: float = 0.5,
        max_cpu_usage: float = 0.60,
        max_ram_usage_gb: float = 4.0
    ):
        self.thresholds = {
            "win_rate": (min_win_rate, "min"),
            "sortino_ratio": (min_sortino, "min"),
            "sharpe_ratio": (min_sharpe, "min"),
            "max_drawdown": (max_drawdown, "max"),
            "recovery_factor_hours": (max_recovery_factor_hours, "max"),
            "latency_ms": (max_latency_ms, "max"),
            "slippage_pips": (max_slippage_pips, "max"),
            "cpu_usage": (max_cpu_usage, "max"),
            "ram_usage_gb": (max_ram_usage_gb, "max")
        }

    def evaluate(self, metrics: Dict[str, float]) -> Tuple[bool, str]:
        """
        Evaluates a dictionary of performance metrics against the strict thresholds.
        If any metric is missing, it fails safely (rejects).
        
        Returns:
            Tuple[bool, str]: (Passed, Reason)
        """
        reasons = []
        for metric_name, (threshold, check_type) in self.thresholds.items():
            if metric_name not in metrics:
                reasons.append(f"Missing required metric: {metric_name}")
                continue
                
            val = metrics[metric_name]
            if check_type == "min" and val < threshold:
                reasons.append(f"{metric_name} ({val:.2f}) below min threshold ({threshold:.2f})")
            elif check_type == "max" and val > threshold:
                reasons.append(f"{metric_name} ({val:.2f}) above max threshold ({threshold:.2f})")
                
        if reasons:
            reason_str = " | ".join(reasons)
            logger.warning(f"BenchmarkGate Rejected: {reason_str}")
            return False, reason_str
            
        return True, "Passed all benchmark thresholds"
