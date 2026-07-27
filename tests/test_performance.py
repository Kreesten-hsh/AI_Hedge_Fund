import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from aegis_trade.engine.performance import PerformanceEngine

def test_performance_engine_basic_metrics():
    engine = PerformanceEngine(risk_free_rate=0.0, periods_per_year=252)
    
    # Create a dummy equity curve
    dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
    equity = pd.Series([100.0, 105.0, 102.0, 110.0, 108.0], index=dates)
    
    # Create dummy trades
    trades = pd.DataFrame([
        {'timestamp': dates[1], 'pnl': 5.0, 'turnover': 105.0, 'exposure': 1},
        {'timestamp': dates[2], 'pnl': -3.0, 'turnover': 102.0, 'exposure': 1},
        {'timestamp': dates[3], 'pnl': 8.0, 'turnover': 110.0, 'exposure': 1},
        {'timestamp': dates[4], 'pnl': -2.0, 'turnover': 108.0, 'exposure': 1},
    ])
    
    report = engine.compute_tearsheet(equity, trades)
    
    # Total return: 108 / 100 - 1 = 0.08 (8%)
    assert pytest.approx(report.total_return) == 0.08
    
    # Win rate: 2 wins, 2 losses -> 50%
    assert report.win_rate == 0.5
    
    # Profit factor: gross profit (13) / gross loss (5) = 2.6
    assert pytest.approx(report.profit_factor) == 2.6
    
    # Max Drawdown: Peak 105 -> Trough 102 (drop of 3 from 105 = 2.85%)
    # Wait, peak is 110, trough after is 108 (drop of 2 from 110 = 1.81%)
    # 3 / 105 = 0.02857
    assert pytest.approx(report.max_drawdown) == 3 / 105
    
    # Average win/loss
    assert pytest.approx(report.average_win) == 6.5
    assert pytest.approx(report.average_loss) == -2.5

def test_performance_engine_empty():
    engine = PerformanceEngine()
    with pytest.raises(ValueError, match="Equity curve is empty"):
        engine.compute_tearsheet(pd.Series(dtype=float))
        
def test_performance_engine_no_trades():
    engine = PerformanceEngine(risk_free_rate=0.0, periods_per_year=252)
    dates = pd.date_range(start="2023-01-01", periods=2, freq="D")
    equity = pd.Series([100.0, 105.0], index=dates)
    
    report = engine.compute_tearsheet(equity) # No trades dataframe
    
    assert pytest.approx(report.total_return) == 0.05
    assert np.isnan(report.profit_factor)
    
def test_performance_engine_zero_variance():
    engine = PerformanceEngine(risk_free_rate=0.0, periods_per_year=252)
    dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
    equity = pd.Series([100.0, 100.0, 100.0, 100.0, 100.0], index=dates)
    
    report = engine.compute_tearsheet(equity)
    
    assert report.total_return == 0.0
    assert report.sharpe_ratio == 0.0
    assert report.max_drawdown == 0.0
