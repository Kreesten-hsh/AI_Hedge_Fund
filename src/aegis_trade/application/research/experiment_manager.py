import logging
import subprocess
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from aegis_trade.domain.research import (
    ResearchExperiment, ExperimentMetadata, ExperimentConfig,
    ExperimentStatus, PromotionStatus
)
from aegis_trade.infrastructure.research.registry import ExperimentRegistryV2

logger = logging.getLogger(__name__)

class ExperimentManager:
    """
    Gouvernance absolue sur le cycle de vie des expériences.
    Gère la création, la promotion et les transitions d'état.
    """
    def __init__(self, registry: ExperimentRegistryV2):
        self.registry = registry

    def _get_git_commit(self) -> str:
        try:
            result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except Exception:
            # Fallback si pas de Git ou erreur
            import os
            return os.environ.get("AEGIS_GIT_COMMIT", "unknown")

    def create_experiment(self, 
                          config: ExperimentConfig, 
                          strategy_name: str,
                          features: list[str],
                          markets: list[str],
                          timeframes: list[str],
                          parameters: dict[str, Any],
                          author: str = "system",
                          parent_id: Optional[str] = None) -> ResearchExperiment:
        """Crée une nouvelle expérience au statut CREATED avec toutes les métadonnées de traçabilité."""
        metadata = ExperimentMetadata(
            strategy_name=strategy_name,
            parameters=parameters,
            features=features,
            markets=markets,
            timeframes=timeframes,
            git_commit=self._get_git_commit(),
            author=author,
            parent_id=parent_id
        )
        
        experiment = ResearchExperiment(
            metadata=metadata,
            config=config,
            status=ExperimentStatus.CREATED,
            promotion_status=PromotionStatus.RESEARCH
        )
        
        self.registry.save_experiment(experiment)
        self.registry.log_audit(experiment.metadata.id, "CREATE", f"Experiment created by {author}")
        return experiment
        
    def promote_experiment(self, experiment_id: str, new_status: PromotionStatus) -> bool:
        """Promeut une expérience vers un nouveau statut si les conditions sont remplies."""
        exp_data = self.registry.load_experiment(experiment_id)
        if not exp_data:
            raise ValueError(f"Experiment {experiment_id} not found in registry.")
            
        passed = False
        result = exp_data.get("result", {})
        if result and result.get("validation_artifact"):
            passed = result["validation_artifact"].get("report", {}).get("is_approved", False)
            
        if not passed and new_status in [PromotionStatus.CANDIDATE, PromotionStatus.APPROVED, PromotionStatus.PAPER_TRADING]:
            raise ValueError("Cannot promote an experiment that failed validation.")
            
        import json
        for filepath in self.registry.registry_dir.glob("exp_*.json"):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get("metadata", {}).get("id") == experiment_id:
                old_status = data.get("promotion_status")
                data["promotion_status"] = new_status.value
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                
                self.registry.log_audit(experiment_id, "PROMOTE", f"From {old_status} to {new_status.value}")
                return True
                
        return False
