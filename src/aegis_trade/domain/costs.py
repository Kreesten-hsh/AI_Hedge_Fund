"""Modèle de coût de transaction — frontière économique d'une stratégie.

Un seuil d'entrée choisi indépendamment du coût rend la recherche de signal
vaine par construction : si le mouvement anticipé est plus petit que le péage
payé pour le capter, l'espérance est négative quelle que soit la qualité du
modèle. Ce module fait du coût une entrée explicite du dimensionnement des
seuils, pas une découverte post-mortem dans le tearsheet.

Concept de domaine pur : aucune dépendance broker. Un adaptateur
d'infrastructure expose son propre coût sous cette forme (voir
`SimulatedBroker.cost_model`).
"""

from __future__ import annotations

from dataclasses import dataclass

BPS_PER_UNIT = 10_000.0


@dataclass(frozen=True, slots=True)
class TransactionCostModel:
    """Coût d'un aller-retour complet, exprimé en fraction du notionnel.

    Le coût pertinent pour une décision d'entrée est celui de l'ALLER-RETOUR :
    ouvrir une position engage mécaniquement de la fermer. Budgéter uniquement
    la jambe d'entrée sous-estime le péage d'un facteur 2 et fait paraître
    rentables des signaux qui ne le sont pas.
    """

    commission_rate: float
    slippage_bps: float

    def __post_init__(self) -> None:
        if self.commission_rate < 0.0:
            raise ValueError(
                f"commission_rate ne peut pas être négatif (reçu {self.commission_rate})."
            )
        if self.slippage_bps < 0.0:
            raise ValueError(
                f"slippage_bps ne peut pas être négatif (reçu {self.slippage_bps})."
            )

    @property
    def one_way_cost(self) -> float:
        """Coût d'une seule jambe : commission + slippage subi."""
        return self.commission_rate + (self.slippage_bps / BPS_PER_UNIT)

    @property
    def round_trip_cost(self) -> float:
        """Coût entrée + sortie. C'est le seuil de rentabilité brut."""
        return 2.0 * self.one_way_cost

    def breakeven_return(self, safety_margin: float = 1.0) -> float:
        """Rendement attendu minimal pour qu'un trade ait une espérance non négative.

        :param safety_margin: Multiplicateur du coût aller-retour. 1.0 = seuil de
            rentabilité strict (espérance nulle avant erreur de prédiction) ;
            > 1.0 exige une marge au-dessus du coût pour absorber l'erreur du
            modèle. Une marge < 1.0 est refusée : elle signifierait viser un
            trade dont le gain espéré ne couvre pas son propre péage.
        """
        if safety_margin < 1.0:
            raise ValueError(
                "safety_margin doit être >= 1.0 : sous le coût aller-retour, "
                f"l'espérance du trade est négative par construction (reçu {safety_margin})."
            )
        return self.round_trip_cost * safety_margin
