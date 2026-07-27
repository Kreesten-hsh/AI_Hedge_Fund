import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class TearsheetReport:
    """
    Serializable report containing institutional performance metrics.
    """
    total_return: float
    cagr: float
    annualized_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    profit_factor: float
    win_rate: float
    average_win: float
    average_loss: float
    expectancy: float
    recovery_factor: float
    exposure_percent: float
    turnover: float
    
    def to_dict(self) -> Dict[str, Any]:
        # Handle nan values mapping to None for JSON serialization
        d = asdict(self)
        for k, v in d.items():
            if pd.isna(v) or np.isnan(v):
                d[k] = None
        return d

class PerformanceEngine:
    """
    Vectorized engine for computing trading performance metrics.
    """
    def __init__(self, risk_free_rate: float = 0.0, periods_per_year: int = 252):
        self.rf = risk_free_rate
        self.ppy = periods_per_year

    def compute_tearsheet(self, equity_curve: pd.Series, trades: pd.DataFrame = None) -> TearsheetReport:
        """
        Computes the TearsheetReport given an equity curve and optional trades data.
        
        Args:
            equity_curve: pd.Series of portfolio values, indexed by datetime.
            trades: pd.DataFrame containing trade execution details (pnl, exposure, turnover).
                    Must have at least 'pnl', 'turnover', 'exposure' (1 for invested, 0 for cash).
        """
        if equity_curve.empty:
            raise ValueError("Equity curve is empty.")
            
        returns = equity_curve.pct_change().dropna()
        
        if returns.empty:
            raise ValueError("Not enough data to calculate returns.")

        # Total Return & CAGR
        total_ret = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        
        years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365.25
        if years > 0:
            cagr = (1 + total_ret) ** (1 / years) - 1
        else:
            cagr = np.nan
            
        # Volatility
        ann_vol = returns.std() * np.sqrt(self.ppy)
        
        # Sharpe
        excess_returns = returns - (self.rf / self.ppy)
        sharpe = (excess_returns.mean() / returns.std()) * np.sqrt(self.ppy) if returns.std() != 0 else 0.0
        
        # Sortino
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(self.ppy)
        sortino = (excess_returns.mean() * self.ppy) / downside_std if (len(downside_returns) > 1 and downside_std != 0) else np.nan

        # Drawdown
        cum_ret = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cum_ret.fillna(1))
        drawdown = (cum_ret - running_max) / running_max
        max_dd = abs(drawdown.min())
        
        # Calmar
        calmar = cagr / max_dd if max_dd > 0 else np.nan
        
        # Recovery Factor
        recovery_factor = total_ret / max_dd if max_dd > 0 else np.nan

        # Trade-based Metrics
        profit_factor = np.nan
        win_rate = np.nan
        avg_win = np.nan
        avg_loss = np.nan
        expectancy = np.nan
        exposure_pct = np.nan
        total_turnover = np.nan
        
        if trades is not None and not trades.empty and 'pnl' in trades.columns:
            wins = trades[trades['pnl'] > 0]['pnl']
            losses = trades[trades['pnl'] < 0]['pnl']
            
            gross_profit = wins.sum()
            gross_loss = abs(losses.sum())
            
            profit_factor = gross_profit / gross_loss if gross_loss != 0 else np.nan
            
            total_trades = len(trades)
            win_rate = len(wins) / total_trades if total_trades > 0 else np.nan
            
            avg_win = wins.mean() if not wins.empty else 0.0
            avg_loss = losses.mean() if not losses.empty else 0.0
            
            # Expectancy = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
            # Actually, usually Expected Value per trade:
            expectancy = trades['pnl'].mean()
            
            if 'exposure' in trades.columns:
                exposure_pct = trades['exposure'].mean() # Assuming 1 is invested, 0 is not
                
            if 'turnover' in trades.columns:
                total_turnover = trades['turnover'].sum()
                
        return TearsheetReport(
            total_return=float(total_ret),
            cagr=float(cagr),
            annualized_volatility=float(ann_vol),
            sharpe_ratio=float(sharpe),
            sortino_ratio=float(sortino),
            max_drawdown=float(max_dd),
            calmar_ratio=float(calmar),
            profit_factor=float(profit_factor),
            win_rate=float(win_rate),
            average_win=float(avg_win),
            average_loss=float(avg_loss),
            expectancy=float(expectancy),
            recovery_factor=float(recovery_factor),
            exposure_percent=float(exposure_pct),
            turnover=float(total_turnover)
        )
