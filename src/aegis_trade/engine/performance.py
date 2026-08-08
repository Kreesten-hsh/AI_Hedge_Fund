import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, Any

TRADING_DAYS_PER_YEAR = 252


def annualization_factor(periods_per_year: int) -> float:
    """
    Facteur d'annualisation d'un écart-type de rendements périodiques : sqrt(periods_per_year).

    AUTORITÉ UNIQUE du Lot 3 pour l'annualisation. Tout appelant qui annualise une volatilité,
    un Sharpe ou un Sortino passe par ici — `engine/portfolio.py` inclus.

    Le facteur ne dépend QUE de la périodicité des rendements, jamais de la longueur de la
    fenêtre observée. `engine/portfolio.py` appliquait auparavant `sqrt(n_periods)` sous 30 jours
    pour « éviter une extrapolation absurde à 252 » : l'intention était juste, la mise en œuvre
    introduisait une discontinuité mesurée d'un facteur **2.95x sur une seule barre de plus**
    (29 jours -> facteur 5.385, 30 jours -> 15.875). Un Sharpe qui triple parce que la fenêtre
    gagne un jour n'est pas comparable d'une exécution à l'autre.

    Le bruit d'estimation d'un Sharpe sur fenêtre courte est réel, mais c'est une réserve
    statistique — elle se traite par un seuil de significativité (le `NaN` sous 2 trades de
    `Portfolio.metrics`), pas en déformant le facteur.
    """
    if periods_per_year <= 0:
        raise ValueError(f"periods_per_year must be strictly positive, got {periods_per_year}")
    return float(np.sqrt(periods_per_year))


def annualized_volatility(returns: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    """Écart-type des rendements périodiques, annualisé."""
    return float(returns.std() * annualization_factor(periods_per_year))


def annualized_sharpe(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """
    Sharpe annualisé. Renvoie 0.0 sur variance nulle — pas d'infini sur un capital immobile.

    Le taux sans risque est déprorratisé (`rf / periods_per_year`) pour être homogène aux
    rendements périodiques avant soustraction.
    """
    std = returns.std()
    if std == 0 or pd.isna(std):
        return 0.0
    excess = returns - (risk_free_rate / periods_per_year)
    return float((excess.mean() / std) * annualization_factor(periods_per_year))


def annualized_sortino(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """
    Sortino annualisé : excès de rendement rapporté au seul écart-type des rendements négatifs.

    Renvoie `NaN` quand la baisse n'est pas estimable (moins de 2 rendements négatifs, ou
    dispersion nulle). Un `inf` serait un ratio « parfait » construit sur une absence de données.
    """
    downside = returns[returns < 0]
    if len(downside) < 2:
        return float("nan")
    downside_std = downside.std() * annualization_factor(periods_per_year)
    if downside_std == 0 or pd.isna(downside_std):
        return float("nan")
    excess = returns - (risk_free_rate / periods_per_year)
    return float((excess.mean() * periods_per_year) / downside_std)


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
            
        # Volatility / Sharpe / Sortino — délégués aux helpers d'autorité de ce module.
        ann_vol = annualized_volatility(returns, self.ppy)
        sharpe = annualized_sharpe(returns, self.rf, self.ppy)
        sortino = annualized_sortino(returns, self.rf, self.ppy)

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
