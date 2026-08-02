import logging
from typing import Type
import numpy as np
from aegis_trade.domain.validation import ValidationCampaignResult, ValidationCampaignType
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.execution import IBroker
from aegis_trade.domain.core import Symbol, TimeFrame, AssetClass
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validators.base import IValidator
from aegis_trade.engine.backtester import Backtester

logger = logging.getLogger(__name__)

class MonteCarloValidator(IValidator):
    """
    Test Monte-Carlo : Simulation bootstrap par rééchantillonnage des PnL de trades.
    Calcule la probabilité réelle de ruine (< 5% exigé).
    """
    def run(
        self, 
        strategy: IStrategy, 
        data_feed: IDataFeed, 
        broker_factory: Type[IBroker], 
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        logger.info(f"Running MonteCarloValidator ({config.monte_carlo_iterations} iterations)...")
        
        broker = broker_factory()
        backtester = Backtester(data_feed=data_feed, strategy=strategy, broker=broker)
        symbol = config.markets[0] if config.markets else Symbol("CRASH1000", AssetClass.INDICES)
        timeframe = config.timeframes[0] if config.timeframes else TimeFrame.M1
        
        try:
            backtester.run(symbol, timeframe)
            trades_pnl = [t['pnl'] for t in backtester.trades_history if not t.get('rejected', False)]
            
            if not trades_pnl:
                # Si aucun trade n'est généré, la stratégie n'est pas validable (aucun trade)
                logger.warning("MonteCarloValidator: Aucun trade généré par la stratégie. Échec de validation.")
                return ValidationCampaignResult(
                    campaign_type=ValidationCampaignType.MONTE_CARLO,
                    metrics={"ruin_probability": 1.0},
                    passed=False,
                    details={"iterations": config.monte_carlo_iterations, "trades_count": 0, "reason": "Aucun trade généré, résultat non concluant"}
                )
                
            rng = np.random.default_rng(config.seed)
            num_trades = len(trades_pnl)
            iterations = min(config.monte_carlo_iterations, 1000)  # cap a 1000 pour rapidite
            starting_cap = backtester.initial_capital
            
            ruin_count = 0
            pnl_array = np.array(trades_pnl, dtype=np.float64)
            
            for _ in range(iterations):
                sample_pnl = rng.choice(pnl_array, size=num_trades, replace=True)
                equity_curve = starting_cap + np.cumsum(sample_pnl)
                if np.any(equity_curve <= (starting_cap * 0.5)):
                    ruin_count += 1
                    
            ruin_prob = float(ruin_count / iterations)
            passed = ruin_prob < 0.05
            
            return ValidationCampaignResult(
                campaign_type=ValidationCampaignType.MONTE_CARLO,
                metrics={"ruin_probability": round(ruin_prob, 4)},
                passed=passed,
                details={"iterations": iterations, "trades_sampled": num_trades}
            )
        except Exception as e:
            logger.error(f"MonteCarloValidator failed: {e}")
            return ValidationCampaignResult(
                campaign_type=ValidationCampaignType.MONTE_CARLO,
                metrics={"ruin_probability": 1.0},
                passed=False,
                details={"error": str(e)}
            )
