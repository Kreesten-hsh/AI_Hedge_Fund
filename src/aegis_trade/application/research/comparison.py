import json
from typing import List, Dict, Any
from aegis_trade.domain.research import ResearchExperiment
from aegis_trade.infrastructure.research.registry import ExperimentRegistryV2

class ExperimentComparator:
    """
    Service comparant plusieurs expériences entre elles selon différentes métriques.
    """
    
    def __init__(self, registry: ExperimentRegistryV2):
        self.registry = registry
        
    def get_all_experiments(self) -> List[Dict[str, Any]]:
        """Charge toutes les expériences du registre."""
        return self.registry.list_experiments()
        
    def extract_metrics(self, experiment_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Extrait les métriques clés pour la comparaison."""
        result = experiment_dict.get("result", {})
        validation_artifact = result.get("validation_artifact") or {}
        report = validation_artifact.get("report") or {}
        
        # On va chercher les métriques dans les campagnes de validation
        campaigns = report.get("campaigns", [])
        
        sharpe = 0.0
        drawdown = 0.0
        win_rate = 0.0
        
        for c in campaigns:
            metrics = c.get("metrics", {})
            if "sharpe_ratio" in metrics:
                sharpe = max(sharpe, metrics["sharpe_ratio"])
            if "max_drawdown" in metrics:
                drawdown = min(drawdown, metrics["max_drawdown"]) # Drawdown is usually negative or minimal
            if "win_rate" in metrics:
                win_rate = max(win_rate, metrics["win_rate"])
                
        return {
            "id": experiment_dict.get("metadata", {}).get("id", "unknown"),
            "strategy": experiment_dict.get("metadata", {}).get("strategy_name", "Unknown"),
            "score": report.get("strategy_score", 0.0),
            "passed": report.get("is_approved", False),
            "sharpe": sharpe,
            "drawdown": drawdown,
            "win_rate": win_rate,
            "params": experiment_dict.get("metadata", {}).get("parameters", {})
        }

    def compare_all(self) -> List[Dict[str, Any]]:
        """Retourne la liste complète des métriques comparées."""
        experiments = self.get_all_experiments()
        return [self.extract_metrics(e) for e in experiments]
