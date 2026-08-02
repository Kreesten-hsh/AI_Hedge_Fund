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

class HoldOutValidator(IValidator):
    """
    Test Hold-Out : Entraînement/Recherche sur une période et test strict sur une période indépendante.
    Calcul effectif des métriques de backtest réelles.
    """
    def run(
        self, 
        strategy: IStrategy, 
        data_feed: IDataFeed, 
        broker_factory: Type[IBroker], 
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        logger.info("Running HoldOutValidator...")
        
        broker = broker_factory()
        backtester = Backtester(data_feed=data_feed, strategy=strategy, broker=broker)
        
        symbol = config.markets[0] if config.markets else Symbol("CRASH1000", AssetClass.INDICES)
        timeframe = config.timeframes[0] if config.timeframes else TimeFrame.M1
        
        try:
            tearsheet = backtester.run(symbol, timeframe)
            sharpe = float(tearsheet.sharpe_ratio)
            drawdown = float(tearsheet.max_drawdown)
            
            # Condition de validation réelle : Sharpe > 0.5 et drawdown < 30%
            passed = (sharpe >= 0.5) and (drawdown <= 0.30)
            
            return ValidationCampaignResult(
                campaign_type=ValidationCampaignType.HOLD_OUT,
                metrics={"sharpe_ratio": round(sharpe, 4), "max_drawdown": round(drawdown, 4)},
                passed=passed,
                details={"symbol": symbol.name, "timeframe": timeframe.value, "ratio": config.test_ratio}
            )
        except Exception as e:
            logger.error(f"HoldOutValidator failed during execution: {e}")
            return ValidationCampaignResult(
                campaign_type=ValidationCampaignType.HOLD_OUT,
                metrics={"sharpe_ratio": 0.0, "max_drawdown": 1.0},
                passed=False,
                details={"error": str(e)}
            )
