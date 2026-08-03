"""Barème de notation d'une stratégie (0-100).

Défaut corrigé ici (voir `docs/ADR/0017-monotonic-strategy-score.md`) : l'ancien
barème était additif, avec des bonus indépendants du résultat économique. Un
bonus Monte-Carlo de +20 points ne regardait que la probabilité de ruine, jamais
la perte réelle — mesuré sur la campagne `val_20260803_063600`, une stratégie à
-37.11 % de rendement obtenait 30/100 quand une stratégie à -1.02 % obtenait 0.
Le rejet ne tenait que par un plafond arbitraire à 49 : un barème non monotone,
donc contournable en désactivant les campagnes critiques.

Construction retenue : **multiplicative**, jamais additive.

    score = economic(net_return) x drawdown_factor x robustness_factor x ruin_factor

Chaque facteur appartient à [0, 1] et ne dépend PAS du rendement net. Le score
est donc strictement croissant en rendement net à facteurs constants : aucune
combinaison de métriques secondaires ne peut faire passer une stratégie
perdante devant une stratégie gagnante. C'est la propriété que l'ancien barème
n'avait pas, et la seule qui rende une validation en aval probante.

Corollaire volontaire : une campagne absente compte comme un échec pondéré.
Sans cela, retirer Monte-Carlo de la configuration augmenterait le score — la
même faille de falsifiabilité déplacée d'un cran.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional

from aegis_trade.domain.validation import ValidationCampaignResult, ValidationCampaignType

logger = logging.getLogger(__name__)

# Clés de métriques attendues des validateurs. Le barème lit le résultat
# économique réel, pas un proxy : `sharpe_ratio` seul ne dit pas si le compte a
# gagné de l'argent après frais.
METRIC_NET_RETURN = "net_return"
METRIC_MAX_DRAWDOWN = "max_drawdown"
METRIC_RUIN_PROBABILITY = "ruin_probability"

# Rendement net qui sature le terme économique. 10 % sur le segment de test :
# au-delà, la différence entre deux stratégies gagnantes se joue sur le risque
# et la robustesse, plus sur l'amplitude du gain.
RETURN_SATURATION_SCALE = 0.10

# Drawdown au-delà duquel le score s'annule. Aligné sur la limite de risque déjà
# appliquée par HoldOutValidator (30 %) : un seul seuil de risque dans le
# système, appliqué ici en continu au lieu d'un drapeau binaire.
MAX_TOLERATED_DRAWDOWN = 0.30

# Campagnes exigées pour un score plein, et leur poids. Les deux campagnes
# hors-échantillon pèsent double : ce sont elles qui portent la preuve.
REQUIRED_CAMPAIGN_WEIGHTS: Dict[ValidationCampaignType, float] = {
    ValidationCampaignType.HOLD_OUT: 2.0,
    ValidationCampaignType.WALK_FORWARD: 2.0,
    ValidationCampaignType.MONTE_CARLO: 1.0,
    ValidationCampaignType.BENCHMARK: 1.0,
}

# Ordre de préférence pour lire le rendement net : le hors-échantillon d'abord.
NET_RETURN_PRECEDENCE = (
    ValidationCampaignType.HOLD_OUT,
    ValidationCampaignType.WALK_FORWARD,
    ValidationCampaignType.BENCHMARK,
)


class ScoringEngine:
    """Agrège les campagnes de validation en un score monotone de 0 à 100.

    Un score >= 75 (seuil d'approbation du `ValidationRunner`) exige
    simultanément : un rendement net nettement positif, un drawdown faible
    devant la limite de risque, et les quatre campagnes du framework passées.
    Aucune de ces conditions ne peut être compensée par une autre.
    """

    def calculate_score(self, campaigns: List[ValidationCampaignResult]) -> float:
        if not campaigns:
            return 0.0

        net_return = self._extract_net_return(campaigns)
        if net_return is None:
            # Absence de mesure n'est pas un résultat neutre : sans rendement net
            # observé, il n'y a rien à noter. Retourner un score moyen ici
            # laisserait une stratégie non mesurée franchir des gates en aval.
            logger.warning(
                "Aucune campagne n'expose '%s' : score nul (résultat non mesurable, "
                "pas neutre).",
                METRIC_NET_RETURN,
            )
            return 0.0

        economic = self._economic_term(net_return)
        drawdown_factor = self._drawdown_factor(campaigns)
        robustness_factor = self._robustness_factor(campaigns)
        ruin_factor = self._ruin_factor(campaigns)

        score = economic * drawdown_factor * robustness_factor * ruin_factor

        logger.info(
            "Score %.2f/100 — net_return=%.4f (terme économique %.2f) x DD %.3f "
            "x robustesse %.3f x anti-ruine %.3f",
            score,
            net_return,
            economic,
            drawdown_factor,
            robustness_factor,
            ruin_factor,
        )
        return min(100.0, max(0.0, score))

    def _extract_net_return(
        self, campaigns: List[ValidationCampaignResult]
    ) -> Optional[float]:
        """Lit le rendement net réel, hors-échantillon en priorité."""
        by_type = {c.campaign_type: c for c in campaigns}
        for campaign_type in NET_RETURN_PRECEDENCE:
            campaign = by_type.get(campaign_type)
            if campaign is None:
                continue
            value = campaign.metrics.get(METRIC_NET_RETURN)
            if value is not None:
                return float(value)
        return None

    def _economic_term(self, net_return: float) -> float:
        """Terme économique dans (0, 100), strictement croissant, 50 à l'équilibre.

        `tanh` borne le score sans introduire de palier : deux stratégies
        perdantes restent ordonnées entre elles (une perte de 1 % note
        strictement au-dessus d'une perte de 37 %), ce qui rend le barème
        exploitable comme diagnostic et non seulement comme portillon.
        """
        return 50.0 * (1.0 + math.tanh(net_return / RETURN_SATURATION_SCALE))

    def _drawdown_factor(self, campaigns: List[ValidationCampaignResult]) -> float:
        """Pénalité continue et proportionnelle au drawdown réel observé.

        On retient le PIRE drawdown rapporté : la contrainte de risque porte sur
        le pire cas traversé, pas sur sa moyenne entre campagnes.
        """
        drawdowns = [
            float(c.metrics[METRIC_MAX_DRAWDOWN])
            for c in campaigns
            if METRIC_MAX_DRAWDOWN in c.metrics
        ]
        if not drawdowns:
            return 1.0
        worst = max(drawdowns)
        return max(0.0, 1.0 - (worst / MAX_TOLERATED_DRAWDOWN))

    def _robustness_factor(self, campaigns: List[ValidationCampaignResult]) -> float:
        """Part pondérée des campagnes exigées effectivement passées.

        Une campagne absente (non configurée, ou tombée en exception dans le
        runner) compte comme un échec. Sans cela, désactiver une campagne
        gênante augmenterait le score.
        """
        passed_types = {c.campaign_type for c in campaigns if c.passed}
        total_weight = sum(REQUIRED_CAMPAIGN_WEIGHTS.values())
        earned = sum(
            weight
            for campaign_type, weight in REQUIRED_CAMPAIGN_WEIGHTS.items()
            if campaign_type in passed_types
        )
        return earned / total_weight

    def _ruin_factor(self, campaigns: List[ValidationCampaignResult]) -> float:
        """Anti-ruine en PÉNALITÉ, jamais en bonus.

        L'ancien barème créditait +20 points pour une probabilité de ruine
        faible : un gain gratuit qu'une stratégie en perte pouvait encaisser.
        Éviter la ruine n'est pas une performance, c'est un prérequis — donc un
        multiplicateur qui ne peut que retirer des points.
        """
        for campaign in campaigns:
            if campaign.campaign_type != ValidationCampaignType.MONTE_CARLO:
                continue
            ruin_probability = campaign.metrics.get(METRIC_RUIN_PROBABILITY)
            if ruin_probability is None:
                continue
            return max(0.0, 1.0 - float(ruin_probability))
        # Monte-Carlo absent : son poids est déjà perdu dans le facteur de
        # robustesse, pas de double peine ici.
        return 1.0
