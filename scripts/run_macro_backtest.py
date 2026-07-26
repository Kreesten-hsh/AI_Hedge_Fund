import os
import sys
import pandas as pd
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.dataset.resolver import DatasetResolver
from aegis_trade.engine.broker import SimulatedBroker
from aegis_trade.engine.core import TradingEngine
from aegis_trade.engine.feed import HistoricalReplayFeed
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.engine.risk import BasicRiskEngine
from aegis_trade.engine.strategy import EmaCrossStrategy
from aegis_trade.strategies.composite_macro import CompositeMacroStrategy

def run_backtest(strategy_name, strategy, dataset_xau, resolver, total_bars):
    print(f"\nRunning backtest for {strategy_name}...")
    feed = HistoricalReplayFeed(dataset_xau, resolver, start_idx=0, end_idx=total_bars)
    risk = BasicRiskEngine(risk_pct=Decimal("0.10"))
    broker = SimulatedBroker(commission_per_unit=Decimal("0.0"), slippage_per_unit=Decimal("0.1"))
    portfolio = Portfolio(initial_capital=10000.0)
    
    engine = TradingEngine(
        feed=feed,
        strategy=strategy,
        broker=broker,
        risk_engine=risk,
        portfolio=portfolio
    )

    report = engine.run()
    metrics = report.metrics
    return metrics

def main():
    repo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "datasets")
    repo = StorageDatasetRepository(repo_path)
    resolver = DatasetResolver(repo)
    
    symbol = "XAUUSD"
    print(f"Loading {symbol} H1 data...")
    dataset_xau = resolver.resolve_latest(symbol, "H1")
    if not dataset_xau:
        print("XAUUSD dataset not found.")
        return
        
    all_bars = resolver.load_data(dataset_xau)
    total_bars = len(all_bars)
    
    print("Loading DXY D1 data...")
    try:
        ds_dxy = resolver.resolve_latest("DXY", "D1")
        dxy_bars = resolver.load_data(ds_dxy) if ds_dxy else []
    except Exception:
        dxy_bars = []
        
    if not dxy_bars:
        print("DXY dataset not found.")
        return

    print("Computing DXY Trend (SMA-5)...")
    df_xau = pd.DataFrame([{"timestamp": b.timestamp} for b in all_bars]).set_index("timestamp")
    
    # Calculate DXY SMA-5 on D1 dataset
    df_dxy = pd.DataFrame([{"timestamp": b.timestamp, "dxy_close": float(b.close)} for b in dxy_bars]).set_index("timestamp")
    df_dxy["dxy_sma5"] = df_dxy["dxy_close"].rolling(5).mean()
    
    # Trend: 1 if Haussier (close > sma), -1 if Baissier (close < sma)
    df_dxy["dxy_trend"] = df_dxy.apply(
        lambda row: 1 if row["dxy_close"] > row["dxy_sma5"] else (-1 if row["dxy_close"] < row["dxy_sma5"] else 0), 
        axis=1
    )
    
    # Align and ffill DXY trend to XAU H1 index
    df_merged = df_xau.join(df_dxy, how="outer")
    df_merged["dxy_trend"] = df_merged["dxy_trend"].ffill()
    df_xau = df_merged.loc[df_xau.index].copy()
    
    macro_data = df_xau["dxy_trend"].to_dict()
    
    # Instantiate strategies
    base_strategy = EmaCrossStrategy(fast_period=20, slow_period=50)
    filtered_strategy = CompositeMacroStrategy(symbol=symbol, fast_period=20, slow_period=50, macro_data=macro_data)
    
    # Run backtests
    base_metrics = run_backtest("EMA Cross (Baseline)", base_strategy, dataset_xau, resolver, total_bars)
    filtered_metrics = run_backtest("Composite Macro Strategy (Filtered)", filtered_strategy, dataset_xau, resolver, total_bars)
    
    # Comparative Report
    print("\n" + "="*80)
    print("MACRO REGIME FILTERING P&L COMPARISON (Slippage: 0.1)")
    print("="*80)
    header = f"{'Metric':<20} | {'EMA Cross (Base)':>20} | {'Composite Macro':>20}"
    print(header)
    print("-" * len(header))
    
    def format_metric(name, m_dict, fmt, suffix=""):
        v = m_dict.get(name, 0.0)
        return f"{v:{fmt}}{suffix}"
    
    metrics_to_print = [
        ("Total Trades", "total_trades", ".0f", ""),
        ("Win Rate", "win_rate", ".2%", ""),
        ("Net Profit", "net_profit", ".2f", " $"),
        ("Profit Factor", "profit_factor", ".2f", ""),
        ("Max Drawdown", "max_drawdown", ".2%", ""),
        ("Sharpe Ratio", "sharpe_ratio", ".2f", ""),
        ("Sortino Ratio", "sortino_ratio", ".2f", ""),
        ("Calmar Ratio", "calmar_ratio", ".2f", "")
    ]
    
    for label, key, fmt, suffix in metrics_to_print:
        # Convert win_rate/max_drawdown to percentages if they are raw ratios (without suffix trickery in dict)
        base_v = base_metrics.get(key, 0.0)
        filt_v = filtered_metrics.get(key, 0.0)
        
        # Handle percentage scaling manually
        if key in ["win_rate", "max_drawdown"]:
            base_v *= 100
            filt_v *= 100
            fmt = ".2f"
            suffix = "%"

        b_str = f"{base_v:{fmt}}{suffix}"
        f_str = f"{filt_v:{fmt}}{suffix}"
        print(f"{label:<20} | {b_str:>20} | {f_str:>20}")
    print("="*80)

if __name__ == "__main__":
    main()
