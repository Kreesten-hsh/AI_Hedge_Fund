import logging
import time
from typing import Type, Callable, Dict, Any

from aegis_trade.domain.research import ExperimentConfig, ExperimentMetadata, ResearchExperiment
from aegis_trade.domain.strategy import IStrategy
from aegis_trade.domain.ports.data_feed import IDataFeed
from aegis_trade.domain.execution import IBroker
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.application.validation.validation_runner import ValidationRunner
from aegis_trade.infrastructure.research.registry import ExperimentRegistryV2

logger = logging.getLogger(__name__)

class ExperimentRunner:
    """
    Orchestrateur qui exécute une expérience de recherche complète.
    Pipeline: Config -> Instanciation Stratégie -> Validation Framework -> Enregistrement du résultat.
    """
    
    def __init__(
        self, 
        registry: ExperimentRegistryV2, 
        validation_runner: ValidationRunner,
        strategy_factory: Callable[[str, Dict[str, Any]], IStrategy],
        data_feed_factory: Callable[[str], IDataFeed],
        broker_factory: Type[IBroker]
    ):
        self.registry = registry
        self.validation_runner = validation_runner
        self.strategy_factory = strategy_factory
        self.data_feed_factory = data_feed_factory
        self.broker_factory = broker_factory
        
    def run_experiment(self, config: ExperimentConfig, metadata_kwargs: Dict[str, Any] = None) -> ResearchExperiment:
        """Exécute l'expérience à partir d'une configuration."""
        start_time = time.time()
        
        # 1. Prepare Metadata
        meta_kwargs = metadata_kwargs or {}
        metadata = ExperimentMetadata(
            strategy_name=config.strategy_class_name,
            parameters=config.strategy_kwargs,
            features=[], # to be filled by the strategy if known
            markets=config.data_sources,
            **meta_kwargs
        )
        experiment = ResearchExperiment(metadata=metadata, config=config)
        
        logger.info(f"Starting Experiment {metadata.id} for {metadata.strategy_name}")
        
        try:
            # 2. Instantiate Strategy
            strategy = self.strategy_factory(config.strategy_class_name, config.strategy_kwargs)
            
            # 3. Instantiate DataFeed (Mocked handling for multiple sources here, just take first)
            data_feed = self.data_feed_factory(config.data_sources[0] if config.data_sources else "default")
            
            # 4. Instantiate ValidationConfig from dict
            val_config = ValidationConfig(**config.validation_config_dict)
            
            # 5. Run Validation Framework
            validation_artifact = self.validation_runner.run_validation(
                strategy=strategy,
                data_feed=data_feed,
                broker_factory=self.broker_factory,
                config=val_config
            )
            
            # 6. Mark Completed
            execution_time = time.time() - start_time
            experiment.mark_completed(validation_artifact, execution_time)
            
        except Exception as e:
            logger.error(f"Experiment {metadata.id} failed: {e}")
            experiment.mark_failed(str(e))
            
        # 7. Save to Registry
        self.registry.save_experiment(experiment)
        
        return experiment
        
    def replay(self, experiment_id: str) -> ResearchExperiment:
        """Rejoue une expérience existante pour garantir la reproductibilité."""
        exp_data = self.registry.load_experiment(experiment_id)
        if not exp_data:
            raise ValueError(f"Experiment {experiment_id} not found in registry.")
            
        # Reconstruire la configuration
        config_data = exp_data.get("config", {})
        config = ExperimentConfig(
            strategy_class_name=config_data.get("strategy_class_name"),
            strategy_kwargs=config_data.get("strategy_kwargs", {}),
            validation_config_dict=config_data.get("validation_config_dict", {}),
            data_sources=config_data.get("data_sources", [])
        )
        
        metadata_kwargs = exp_data.get("metadata", {})
        # On s'assure de réutiliser le même seed etc.
        
        logger.info(f"Replaying Experiment {experiment_id}")
        return self.run_experiment(config, metadata_kwargs=metadata_kwargs)
