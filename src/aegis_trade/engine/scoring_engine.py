import logging
from typing import List
from aegis_trade.domain.validation import ValidationCampaignResult, ValidationCampaignType

logger = logging.getLogger(__name__)

class ScoringEngine:
    """
    Isole la logique mathématique de la notation d'une stratégie (Strategy Score de 0 à 100).
    Agrége les métriques issues des différentes campagnes de validation.
    """
    
    def calculate_score(self, campaigns: List[ValidationCampaignResult]) -> float:
        """
        Calcule le score global basé sur une pondération des différents validateurs.
        """
        if not campaigns:
            return 0.0
            
        score = 0.0
        
        # Exemple de pondération extensible
        # Pour cet exemple, on cherche le Sharpe ratio et le win rate dans les métriques.
        # Plus tard, on peut remplacer par Calmar ratio ou introduire des pénalités de DD.
        
        for c in campaigns:
            # 1. Base score per campaign (PASS = 10 points)
            if c.passed:
                score += 10.0
                
            # 2. Metric contributions
            sharpe = c.metrics.get('sharpe_ratio', 0.0)
            if sharpe > 1.0:
                score += min(15.0, sharpe * 5.0) # Max 15 points for Sharpe
                
            # Bonus pour le Monte Carlo (stabilité)
            if c.campaign_type == ValidationCampaignType.MONTE_CARLO:
                ruin_prob = c.metrics.get('ruin_probability', 1.0)
                if ruin_prob < 0.05:
                    score += 20.0
                    
            # Bonus pour le Benchmark (Surperformance)
            if c.campaign_type == ValidationCampaignType.BENCHMARK:
                alpha = c.metrics.get('alpha', 0.0)
                if alpha > 0:
                    score += 15.0

        # Normalisation arbitraire sur 100 pour l'instant
        final_score = min(100.0, max(0.0, score))
        
        # Penalties: Si une campagne critique FAIL, le score global est capé à 50
        critical_campaigns = [ValidationCampaignType.WALK_FORWARD, ValidationCampaignType.HOLD_OUT]
        for c in campaigns:
            if c.campaign_type in critical_campaigns and not c.passed:
                logger.warning(f"Critical campaign {c.campaign_type} failed. Capping score at 49.")
                final_score = min(final_score, 49.0)
                
        return final_score
