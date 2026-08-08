import logging
from datetime import datetime, timezone
from typing import Callable, Dict

from aegis_trade.domain.validation import (
    ValidationContext, ValidationArtifact, ValidationReport, ValidationCampaignType
)
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.execution import IBroker
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.engine.scoring_engine import ScoringEngine
from aegis_trade.infrastructure.validation.registry import ValidationRegistry
from aegis_trade.application.validation.validators.base import IValidator
from aegis_trade.application.validation.validators.hold_out_validator import HoldOutValidator
from aegis_trade.application.validation.validators.walk_forward_validator import WalkForwardValidator
from aegis_trade.application.validation.validators.monte_carlo_validator import MonteCarloValidator
from aegis_trade.application.validation.validators.benchmark_validator import BenchmarkValidator
from aegis_trade.application.validation.validators.multi_validators import MultiMarketValidator, MultiTimeframeValidator

logger = logging.getLogger(__name__)

class ValidationRunner:
    """
    Orchestrateur global du Framework de Validation Institutionnelle.
    Exécute les différentes campagnes de validation, génère le rapport et l'enregistre.
    """
    
    def __init__(self, registry: ValidationRegistry, scoring_engine: ScoringEngine):
        self.registry = registry
        self.scoring_engine = scoring_engine
        
        # Factory of validators
        self._validators: Dict[ValidationCampaignType, IValidator] = {
            ValidationCampaignType.HOLD_OUT: HoldOutValidator(),
            ValidationCampaignType.WALK_FORWARD: WalkForwardValidator(),
            ValidationCampaignType.MONTE_CARLO: MonteCarloValidator(),
            ValidationCampaignType.BENCHMARK: BenchmarkValidator(),
            ValidationCampaignType.MULTI_MARKET: MultiMarketValidator(),
            ValidationCampaignType.MULTI_TIMEFRAME: MultiTimeframeValidator()
        }
        
    def run_validation(
        self,
        strategy: IStrategy,
        data_feed: IDataFeed,
        broker_factory: Callable[[], IBroker],
        config: ValidationConfig
    ) -> ValidationArtifact:
        
        logger.info("Initializing Validation Framework Run...")
        
        # 1. Capture Execution Context for Reproducibility
        git_ver = "unknown"
        try:
            import subprocess
            git_ver = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            git_ver = "v1.0.0-git-fallback"

        data_h = "hash_empty_data"
        try:
            import glob, hashlib
            hasher = hashlib.sha256()
            for p in sorted(glob.glob("data/market_data/*.parquet")):
                with open(p, "rb") as f:
                    hasher.update(f.read())
            data_h = hasher.hexdigest()[:16]
        except Exception:
            data_h = "hash_fallback_1234"

        context = ValidationContext(
            seed=config.seed,
            git_version=git_ver,
            strategy_version=strategy.__class__.__name__,
            config_version="v1",
            data_hash=data_h,
            timestamp=datetime.now(timezone.utc)
        )
        
        # 2. Execute active campaigns
        campaign_results = []
        for campaign_type in config.active_campaigns:
            validator = self._validators.get(campaign_type)
            if not validator:
                logger.warning(f"Validator for {campaign_type} not implemented.")
                continue
                
            try:
                result = validator.run(
                    strategy=strategy,
                    data_feed=data_feed,
                    broker_factory=broker_factory,
                    config=config
                )
                campaign_results.append(result)
            except Exception as e:
                logger.error(f"Campaign {campaign_type} failed critically: {e}")
                # We do not crash the whole runner, we just miss the campaign (or record failure)
        
        # 3. Calculate Strategy Score
        score = self.scoring_engine.calculate_score(campaign_results)
        is_approved = score >= 75.0 # Threshold for institutional approval
        
        logger.info(f"Validation completed. Final Strategy Score: {score}/100. Approved: {is_approved}")
        
        # 4. Generate Report and Artifact
        report = ValidationReport(
            campaigns=campaign_results,
            strategy_score=score,
            is_approved=is_approved
        )
        
        artifact = ValidationArtifact(
            context=context,
            report=report,
            parameters={"config": config.__dict__} # Simplify for mock
        )
        
        # 5. Save to Registry
        self.registry.save_artifact(artifact)
        
        return artifact
