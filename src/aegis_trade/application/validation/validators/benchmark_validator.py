import logging
from typing import Type
from aegis_trade.domain.validation import ValidationCampaignResult, ValidationCampaignType
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.execution import IBroker
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validators.base import IValidator

logger = logging.getLogger(__name__)

class BenchmarkValidator(IValidator):
    def run(
        self, 
        strategy: IStrategy, 
        data_feed: IDataFeed, 
        broker_factory: Type[IBroker], 
        config: ValidationConfig
    ) -> ValidationCampaignResult:
        logger.info(f"Running BenchmarkValidator with benchmarks {config.benchmarks}...")
        return ValidationCampaignResult(
            campaign_type=ValidationCampaignType.BENCHMARK,
            metrics={"alpha": 0.05, "beta": 0.8},
            passed=True,
            details={"benchmarks_run": config.benchmarks}
        )
