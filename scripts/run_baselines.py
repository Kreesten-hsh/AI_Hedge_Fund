import os
from decimal import Decimal
import pandas as pd

from aegis_trade.dataset.repository import StorageDatasetRepository
from aegis_trade.dataset.resolver import DatasetResolver
from aegis_trade.engine.broker import SimulatedBroker
from aegis_trade.engine.core import TradingEngine
from aegis_trade.engine.feed import HistoricalReplayFeed
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.engine.risk import BasicRiskEngine
from aegis_trade.engine.strategy import EmaCrossStrategy, RsiEmaStrategy, BuyAndHoldStrategy, Return5MomentumStrategy
import numpy as np
import math

def run_backtest(symbol: str, strategy, start_idx: int, end_idx: int, resolver: DatasetResolver) -> dict:
    dataset = resolver.resolve_latest(symbol, "H1")
    
    feed = HistoricalReplayFeed(dataset, resolver, start_idx=start_idx, end_idx=end_idx)
    risk = BasicRiskEngine(risk_pct=Decimal("0.10"))
    
    # Simple commission/slippage model
    # XAUUSD usually has a wider spread. Let's make it 0.1 for Gold, 0.0001 for EURUSD
    slippage = Decimal("0.1") if symbol == "XAUUSD" else Decimal("0.0001")
    broker = SimulatedBroker(commission_per_unit=Decimal("0.0"), slippage_per_unit=slippage)
    
    portfolio = Portfolio(initial_capital=10000.0)
    
    engine = TradingEngine(
        feed=feed,
        strategy=strategy,
        broker=broker,
        risk_engine=risk,
        portfolio=portfolio
    )

    report = engine.run()
    return report.metrics

import argparse

def main():
    parser = argparse.ArgumentParser(description="Run baseline strategies.")
    parser.add_argument("--symbols", nargs="+", default=["XAUUSD"], help="List of symbols")
    parser.add_argument("--timeframe", type=str, default="H1", help="Timeframe (e.g., H1)")
    args = parser.parse_args()

    repo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "datasets")
    repo = StorageDatasetRepository(repo_path)
    resolver = DatasetResolver(repo)
    
    symbols = args.symbols
    strategies = [
        ("EMA Cross", lambda: EmaCrossStrategy(fast_period=20, slow_period=50)),
        ("RSI+EMA", lambda: RsiEmaStrategy(fast_period=20, slow_period=50, rsi_period=14)),
        ("Return5", lambda: Return5MomentumStrategy()),
        ("Buy & Hold", lambda: BuyAndHoldStrategy()),
    ]
    
    results = []
    
    for symbol in symbols:
        try:
            dataset = resolver.resolve_latest(symbol, args.timeframe)
            total_bars = dataset.row_count
            if total_bars == 0:
                continue
                
            chunk_size = total_bars // 12
            
            periods = []
            for i in range(12):
                start_idx = i * chunk_size
                end_idx = start_idx + chunk_size if i < 11 else total_bars
                periods.append((f"Month {i+1} ({start_idx}-{end_idx})", start_idx, end_idx))
                
        except Exception as e:
            print(f"Skipping {symbol}: {e}")
            continue
        for period_name, start_idx, end_idx in periods:
            for strat_name, strat_factory in strategies:
                print(f"Running {symbol} | {period_name} | {strat_name}...")
                metrics = run_backtest(symbol, strat_factory(), start_idx, end_idx, resolver)
                
                results.append({
                    "Symbol": symbol,
                    "Period": period_name,
                    "Strategy": strat_name,
                    "Net Profit": f"{metrics.get('net_profit', 0.0):.2f}",
                    "Win Rate": f"{metrics.get('win_rate', 0.0)*100:.1f}%",
                    "PF": f"{metrics.get('profit_factor', 0.0):.2f}",
                    "Max DD": f"{metrics.get('max_drawdown', 0.0)*100:.2f}%",
                    "Trades": metrics.get('total_trades', 0),
                    "Sharpe": f"{metrics.get('sharpe_ratio', 0.0):.2f}",
                    "Sortino": f"{metrics.get('sortino_ratio', 0.0):.2f}",
                    "Calmar": f"{metrics.get('calmar_ratio', 0.0):.2f}",
                })
                
    df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("BASELINE METRICS")
    print("="*80)
    print(df.to_markdown(index=False))

    # --- Statistical Validation ---
    print("\n" + "="*80)
    print("STATISTICAL VALIDATION (Return5 vs EMA Cross)")
    print("="*80)

    ema_pnls = []
    ret5_pnls = []
    
    # Extract overall metrics to help with decision
    ema_metrics = {"pf": [], "sharpe": [], "dd": []}
    ret5_metrics = {"pf": [], "sharpe": [], "dd": []}

    for res in results:
        pnl = float(res["Net Profit"])
        pf = float(res["PF"])
        sharpe = float(res["Sharpe"])
        dd = float(res["Max DD"].replace("%", ""))

        if res["Strategy"] == "EMA Cross":
            ema_pnls.append(pnl)
            ema_metrics["pf"].append(pf)
            ema_metrics["sharpe"].append(sharpe)
            ema_metrics["dd"].append(dd)
        elif res["Strategy"] == "Return5":
            ret5_pnls.append(pnl)
            ret5_metrics["pf"].append(pf)
            ret5_metrics["sharpe"].append(sharpe)
            ret5_metrics["dd"].append(dd)

    def calc_stats(pnls):
        n = len(pnls)
        if n == 0:
            return 0, 0, 0, 0, (0, 0)
        mean_pnl = np.mean(pnls)
        std_pnl = np.std(pnls, ddof=1) if n > 1 else 0
        pos_windows = sum(1 for p in pnls if p > 0)
        # T-stat against 0
        t_stat = (mean_pnl / (std_pnl / math.sqrt(n))) if std_pnl > 0 else float('nan')
        
        # 95% CI (approximate using t_crit ~ 2.2 for dof=11)
        margin = 2.2 * (std_pnl / math.sqrt(n)) if std_pnl > 0 else 0
        ci = (mean_pnl - margin, mean_pnl + margin)
        
        return pos_windows, mean_pnl, std_pnl, t_stat, ci

    ema_pos, ema_mean, ema_std, ema_tstat, ema_ci = calc_stats(ema_pnls)
    ret5_pos, ret5_mean, ret5_std, ret5_tstat, ret5_ci = calc_stats(ret5_pnls)

    print(f"{'Metric':<25} | {'EMA Cross':<20} | {'Return5':<20}")
    print("-" * 70)
    print(f"{'Positive Windows':<25} | {ema_pos}/{len(ema_pnls):<18} | {ret5_pos}/{len(ret5_pnls):<18}")
    print(f"{'Mean P&L':<25} | {ema_mean:<20.2f} | {ret5_mean:<20.2f}")
    print(f"{'Std Dev P&L':<25} | {ema_std:<20.2f} | {ret5_std:<20.2f}")
    print(f"{'T-Stat (H0: PnL <= 0)':<25} | {ema_tstat:<20.2f} | {ret5_tstat:<20.2f}")
    print(f"{'95% CI':<25} | [{ema_ci[0]:.2f}, {ema_ci[1]:.2f}]      | [{ret5_ci[0]:.2f}, {ret5_ci[1]:.2f}]")
    
    # Compute aggregates for decision
    avg_ema_pf = np.mean(ema_metrics["pf"])
    avg_ret5_pf = np.mean(ret5_metrics["pf"])
    
    avg_ema_sharpe = np.mean(ema_metrics["sharpe"])
    avg_ret5_sharpe = np.mean(ret5_metrics["sharpe"])
    
    avg_ema_dd = np.mean(ema_metrics["dd"])
    avg_ret5_dd = np.mean(ret5_metrics["dd"])

    print("\n" + "="*80)
    print("DECISION")
    print("="*80)

    # Decision criteria:
    # - Profit Factor > 1 (on average)
    # - Sharpe > baseline EMA
    # - Drawdown reasonable (e.g. not drastically worse than EMA, or strictly < 10%)
    # - t-stat increases (ret5_tstat > ema_tstat)

    is_validated = False
    
    # We will compute the sum of P&L too as a simple baseline check
    total_ret5_pnl = sum(ret5_pnls)

    if total_ret5_pnl > 0 and avg_ret5_pf > 1.0 and avg_ret5_sharpe > avg_ema_sharpe and ret5_tstat > ema_tstat:
        # DD check: average DD should be < 15% (which is generally "reasonable" in this context)
        if avg_ret5_dd < 15.0:
            is_validated = True

    if is_validated:
        print("VALIDATED\n")
        print("Return5 est confirmé comme signal exploitable.")
        print("La prochaine PR sera un Regime Analyst unique utilisant Return5 comme entrée principale.")
    else:
        print("REJECTED\n")
        print("Return5 est statistiquement corrélé mais non économiquement exploitable.")
        print("Le projet retourne en Alpha Research afin d'identifier de nouvelles features.")
        
    print("\nReasoning metrics for validation:")
    print(f"- Avg Profit Factor: {avg_ret5_pf:.2f} (> 1.0 required)")
    print(f"- Avg Sharpe: {avg_ret5_sharpe:.2f} (must be > {avg_ema_sharpe:.2f})")
    print(f"- T-Stat: {ret5_tstat:.2f} (must be > {ema_tstat:.2f})")
    print(f"- Avg DD: {avg_ret5_dd:.2f}% (must be reasonable)")

if __name__ == "__main__":
    main()
