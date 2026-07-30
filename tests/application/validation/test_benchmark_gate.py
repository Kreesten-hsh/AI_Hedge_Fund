import pytest
from aegis_trade.application.validation.benchmark_gate import BenchmarkGate

def test_benchmark_gate_passes_when_metrics_exceed_thresholds():
    gate = BenchmarkGate(min_win_rate=0.55, min_sortino=1.2)
    metrics = {
        "win_rate": 0.60,
        "sortino_ratio": 1.5,
        "sharpe_ratio": 1.0 # Ignored by this gate
    }
    
    passed, reason = gate.evaluate(metrics)
    assert passed is True
    assert "Passed" in reason

def test_benchmark_gate_fails_when_win_rate_low():
    gate = BenchmarkGate(min_win_rate=0.55, min_sortino=1.2)
    metrics = {
        "win_rate": 0.50, # Fails
        "sortino_ratio": 1.5
    }
    
    passed, reason = gate.evaluate(metrics)
    assert passed is False
    assert "Win Rate (0.50) below threshold" in reason

def test_benchmark_gate_fails_when_sortino_low():
    gate = BenchmarkGate(min_win_rate=0.55, min_sortino=1.2)
    metrics = {
        "win_rate": 0.60,
        "sortino_ratio": 1.0 # Fails
    }
    
    passed, reason = gate.evaluate(metrics)
    assert passed is False
    assert "Sortino Ratio (1.00) below threshold" in reason

def test_benchmark_gate_fails_when_metrics_missing():
    gate = BenchmarkGate(min_win_rate=0.55, min_sortino=1.2)
    metrics = {} # Missing metrics default to 0.0
    
    passed, reason = gate.evaluate(metrics)
    assert passed is False
    assert "Win Rate (0.00)" in reason
    assert "Sortino Ratio (0.00)" in reason
