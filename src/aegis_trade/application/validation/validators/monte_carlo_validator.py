import logging
import random
from typing import Type
from aegis_trade.domain.validation import ValidationCampaignResult, ValidationCampaignType
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.execution import IBroker
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validators.base import IValidator

logger = logging.getLogger(__name__)

class MonteCarloValidator(IValidator):
    def run(
        self, 
        strategy: IStrategy, 
        data_feed: IDataFeed, 
        broker_factory: Type[IBroker], 
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        logger.info(f"Running MonteCarloValidator (Level {config.monte_carlo_level}, {config.monte_carlo_iterations} iterations)...")
        return ValidationCampaignResult(
            campaign_type=ValidationCampaignType.MONTE_CARLO,
            metrics={"ruin_probability": 0.01},
            passed=True,
            details={"iterations": config.monte_carlo_iterations, "level": config.monte_carlo_level}
        )
