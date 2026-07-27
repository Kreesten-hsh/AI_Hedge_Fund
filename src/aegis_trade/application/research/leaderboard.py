import json
from typing import List, Dict, Any, Callable
from pathlib import Path
from aegis_trade.application.research.comparison import ExperimentComparator

class Leaderboard:
    """
    Classe le résultat des expériences quantitatives.
    """
    def __init__(self, comparator: ExperimentComparator):
        self.comparator = comparator
        
    def generate_ranking(self, sort_key: str = "score", reverse: bool = True) -> List[Dict[str, Any]]:
        """
        Génère un classement des expériences basé sur une métrique.
        """
        metrics_list = self.comparator.compare_all()
        # Default fallback to 0.0 if key is missing or not comparable
        return sorted(metrics_list, key=lambda x: x.get(sort_key, 0.0), reverse=reverse)

class ReportGenerator:
    """
    Génère des rapports formatés (Markdown / JSON) depuis le Leaderboard.
    """
    def __init__(self, leaderboard: Leaderboard, report_dir: str = ".research_registry"):
        self.leaderboard = leaderboard
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_markdown(self) -> str:
        """Produit un rapport Markdown du Leaderboard."""
        ranking = self.leaderboard.generate_ranking()
        
        md = ["# Aegis Quant OS - Research Leaderboard", ""]
        md.append("Classement généré automatiquement.\n")
        
        for idx, exp in enumerate(ranking, 1):
            status = "PASS" if exp["passed"] else "FAIL"
            md.append(f"## {idx}. {exp['strategy']}")
            md.append(f"- **Status** : {status}")
            md.append(f"- **Score** : {exp['score']}/100")
            md.append(f"- **Sharpe** : {exp['sharpe']:.2f}")
            md.append(f"- **Win Rate** : {exp['win_rate']:.2f}")
            md.append(f"- **Paramètres** : `{json.dumps(exp['params'])}`")
            md.append(f"- **ID** : {exp['id']}\n")
            
        filepath = self.report_dir / "leaderboard.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(md))
            
        return str(filepath)
