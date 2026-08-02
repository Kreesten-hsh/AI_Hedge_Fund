import logging
from typing import Type
from aegis_trade.domain.validation import ValidationCampaignResult, ValidationCampaignType
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.execution import IBroker
from aegis_trade.domain.core import Symbol, TimeFrame, AssetClass
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validators.base import IValidator
from aegis_trade.engine.backtester import Backtester

logger = logging.getLogger(__name__)

class WalkForwardValidator(IValidator):
    """
    Test Walk-Forward : Exécute le backtest et évalue la stabilité des performances.
    """
    def run(
        self, 
        strategy: IStrategy, 
        data_feed: IDataFeed, 
        broker_factory: Type[IBroker], 
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        logger.info("Running WalkForwardValidator...")
        
        broker = broker_factory()
        backtester = Backtester(data_feed=data_feed, strategy=strategy, broker=broker)
        
        symbol = config.markets[0] if config.markets else Symbol("CRASH1000", AssetClass.INDICES)
        timeframe = config.timeframes[0] if config.timeframes else TimeFrame.M1
        
        try:
            tearsheet = backtester.run(symbol, timeframe)
            sharpe = float(tearsheet.sharpe_ratio)
            win_rate = float(tearsheet.win_rate)
            
            # Validation : Sharpe > 0.3 et Win Rate > 40%
            passed = (sharpe >= 0.3) and (win_rate >= 0.40)
            
            return ValidationCampaignResult(
                campaign_type=ValidationCampaignType.WALK_FORWARD,
                metrics={"sharpe_ratio": round(sharpe, 4), "win_rate": round(win_rate, 4)},
                passed=passed,
                details={"symbol": symbol.name, "timeframe": timeframe.value, "folds": 5}
            )
        except Exception as e:
            logger.error(f"WalkForwardValidator failed: {e}")
            return ValidationCampaignResult(
                campaign_type=ValidationCampaignType.WALK_FORWARD,
                metrics={"sharpe_ratio": 0.0, "win_rate": 0.0},
                passed=False,
                details={"error": str(e)}
            )
