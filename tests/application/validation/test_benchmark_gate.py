import pytest
from aegis_trade.application.validation.benchmark_gate import BenchmarkGate

def test_benchmark_gate_passes_when_all_metrics_meet_strict_thresholds():
    gate = BenchmarkGate()
    metrics = {
        "win_rate": 0.86,
        "sortino_ratio": 2.1,
        "sharpe_ratio": 1.6,
        "max_drawdown": 0.04,
        "recovery_factor_hours": 24.0,
        "latency_ms": 15.0,
        "slippage_pips": 0.3,
        "cpu_usage": 0.50,
        "ram_usage_gb": 3.0
    }
    
    passed, reason = gate.evaluate(metrics)
    assert passed is True
    assert "Passed" in reason

def test_benchmark_gate_rejects_model_passing_old_lax_thresholds():
    gate = BenchmarkGate() # uses new strict defaults
    # These metrics would pass under the old 0.55/1.2 limits, but fail now
    metrics = {
        "win_rate": 0.62,
        "sortino_ratio": 1.5,
        "sharpe_ratio": 1.6,
        "max_drawdown": 0.04,
        "recovery_factor_hours": 24.0,
        "latency_ms": 15.0,
        "slippage_pips": 0.3,
        "cpu_usage": 0.50,
        "ram_usage_gb": 3.0
    }
    
    passed, reason = gate.evaluate(metrics)
    assert passed is False
    assert "win_rate (0.62) below min threshold (0.85)" in reason
    assert "sortino_ratio (1.50) below min threshold (2.00)" in reason

def test_benchmark_gate_fails_when_metrics_missing():
    gate = BenchmarkGate()
    metrics = {
        "win_rate": 0.86,
        # Missing sortino_ratio and others
    }
    
    passed, reason = gate.evaluate(metrics)
    assert passed is False
    assert "Missing required metric: sortino_ratio" in reason
    assert "Missing required metric: sharpe_ratio" in reason

