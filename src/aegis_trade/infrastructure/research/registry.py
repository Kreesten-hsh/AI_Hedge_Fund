import json
import logging
from pathlib import Path
from dataclasses import asdict
from typing import List, Optional, Dict, Any
from datetime import datetime

from aegis_trade.domain.research import ResearchExperiment, ExperimentStatus, PromotionStatus
from aegis_trade.domain.core import Symbol, TimeFrame

logger = logging.getLogger(__name__)

class ExperimentRegistryV2:
    """
    Service d'historisation des expériences de recherche (V2).
    Permet la sauvegarde, la recherche, le chargement, et gère un audit log.
    """
    def __init__(self, registry_dir: str = ".research_registry"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path = self.registry_dir / "audit.log"
        
    def _generate_filename(self, experiment: ResearchExperiment) -> str:
        timestamp = experiment.metadata.timestamp.strftime("%Y%m%d_%H%M%S")
        strategy_name = experiment.metadata.strategy_name
        score = int(experiment.result.score)
        uid = str(experiment.metadata.id)[:8]
        return f"exp_{timestamp}_{strategy_name}_score_{score}_{uid}.json"
        
    def log_audit(self, experiment_id: str, action: str, details: str):
        """Historise une opération sur une expérience."""
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] EXP: {experiment_id} | ACTION: {action} | DETAILS: {details}\n"
        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def save_experiment(self, experiment: ResearchExperiment) -> str:
        """Sauvegarde l'expérience complète en JSON."""
        filename = self._generate_filename(experiment)
        filepath = self.registry_dir / filename
        
        def _default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if hasattr(obj, 'value'): # For Enums
                return obj.value
            return str(obj)
            
        data = asdict(experiment)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, default=_default_serializer)
            logger.info(f"ResearchExperiment saved to {filepath}")
            self.log_audit(experiment.metadata.id, "SAVE", f"Saved to {filename} with status {experiment.status.value}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save ResearchExperiment: {e}")
            raise
            
    def load_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Charge une expérience depuis le registre (retourne le dictionnaire brut pour l'instant)."""
        for filepath in self.registry_dir.glob("exp_*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("metadata", {}).get("id") == experiment_id:
                        return data
            except Exception:
                continue
        return None

    def list_experiments(self) -> List[Dict[str, Any]]:
        """Retourne la liste complète des expériences sous forme de dictionnaire."""
        experiments = []
        for filepath in self.registry_dir.glob("exp_*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    experiments.append(json.load(f))
            except Exception:
                continue
        return experiments

    def search(self, status: Optional[ExperimentStatus] = None, 
                     promotion_status: Optional[PromotionStatus] = None, 
                     author: Optional[str] = None,
                     parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Filtre les expériences selon plusieurs critères."""
        all_exps = self.list_experiments()
        results = []
        for exp in all_exps:
            match = True
            if status and exp.get("status") != status.value:
                match = False
            if promotion_status and exp.get("promotion_status") != promotion_status.value:
                match = False
            if author and exp.get("metadata", {}).get("author") != author:
                match = False
            if parent_id and exp.get("metadata", {}).get("parent_id") != parent_id:
                match = False
                
            if match:
                results.append(exp)
                
        return results
