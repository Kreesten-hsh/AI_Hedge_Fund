import logging
from typing import Callable, List
import numpy as np
from aegis_trade.domain.validation import ValidationCampaignResult, ValidationCampaignType
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.signal import Signal
from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.execution import IBroker
from aegis_trade.domain.core import Symbol, TimeFrame, AssetClass
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validators.base import IValidator
from aegis_trade.engine.backtester import Backtester

logger = logging.getLogger(__name__)

class BuyAndHoldStrategy(IStrategy):
    """Stratégie benchmark simple : achète à la première barre et conserve."""
    def __init__(self) -> None:
        self._bought = False

    def generate_signals(self, features: FeatureSet) -> List[Signal]:
        if not self._bought:
            self._bought = True
            return [
                Signal(
                    symbol=features.symbol,
                    direction=1,
                    strength=1.0,
                    timestamp=features.timestamp
                )
            ]
        return []

class BenchmarkValidator(IValidator):
    """
    Test Benchmark : Compare la surperformance réelle (Alpha) et le risque relatif (Beta)
    de la stratégie candidate par rapport à la stratégie Benchmark Buy & Hold sur les mêmes données.
    """
    def run(
        self, 
        strategy: IStrategy, 
        data_feed: IDataFeed, 
        broker_factory: Callable[[], IBroker],
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        logger.info(f"Running BenchmarkValidator ({config.benchmarks})...")
        
        symbol = config.markets[0] if config.markets else Symbol("CRASH1000", AssetClass.INDICES)
        timeframe = config.timeframes[0] if config.timeframes else TimeFrame.M1
        
        try:
            # 1. Backtest de la stratégie candidate
            broker_strat = broker_factory()
            backtester_strat = Backtester(data_feed=data_feed, strategy=strategy, broker=broker_strat)
            tearsheet_strat = backtester_strat.run(symbol, timeframe)
            
            strat_return = float(tearsheet_strat.total_return)
            strat_sharpe = float(tearsheet_strat.sharpe_ratio)
            
            # 2. Backtest de la stratégie Buy & Hold (Benchmark)
            broker_bench = broker_factory()
            backtester_bench = Backtester(data_feed=data_feed, strategy=BuyAndHoldStrategy(), broker=broker_bench)
            tearsheet_bench = backtester_bench.run(symbol, timeframe)
            
            bench_return = float(tearsheet_bench.total_return)
            bench_sharpe = float(tearsheet_bench.sharpe_ratio)
            
            # 3. Calculs réels d'Alpha et Beta
            # Alpha = Rendement Stratégie - Rendement Benchmark
            alpha = strat_return - bench_return
            
            # Beta = Ratio des volatilités relatives des courbes d'équité (sans constante codée en dur)
            eq_strat = np.array(list(backtester_strat.equity_curve.values()), dtype=np.float64)
            eq_bench = np.array(list(backtester_bench.equity_curve.values()), dtype=np.float64)
            
            if len(eq_strat) > 1 and len(eq_bench) > 1:
                ret_strat = np.diff(eq_strat) / eq_strat[:-1]
                ret_bench = np.diff(eq_bench) / eq_bench[:-1]
                
                var_bench = float(np.var(ret_bench))
                if var_bench > 1e-8:
                    beta = float(np.cov(ret_strat, ret_bench)[0, 1] / var_bench)
                else:
                    beta = 1.0
            else:
                beta = 1.0

            # Condition de surperformance : Alpha >= 0 (égalise ou surperforme le benchmark) et Sharpe supérieur ou égal
            passed = (alpha >= 0.0) and (strat_sharpe >= bench_sharpe)
            
            return ValidationCampaignResult(
                campaign_type=ValidationCampaignType.BENCHMARK,
                metrics={
                    "alpha": round(alpha, 4),
                    "beta": round(beta, 4),
                    "strategy_sharpe": round(strat_sharpe, 4),
                    "benchmark_sharpe": round(bench_sharpe, 4),
                    "net_return": round(strat_return, 6)
                },
                passed=passed,
                details={
                    "benchmarks_run": ["buy_and_hold"],
                    "strategy_return": round(strat_return, 4),
                    "benchmark_return": round(bench_return, 4)
                }
            )
        except Exception as e:
            logger.error(f"BenchmarkValidator failed: {e}")
            return ValidationCampaignResult(
                campaign_type=ValidationCampaignType.BENCHMARK,
                metrics={"alpha": -1.0, "beta": 1.0, "net_return": -1.0},
                passed=False,
                details={"error": str(e)}
            )
