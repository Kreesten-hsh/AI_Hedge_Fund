"""Faisabilité économique d'un couple (marché, horizon) avant toute modélisation.

Motivé par le rejet documenté dans `docs/ADR/0019-one-bar-horizon-hypothesis-rejected.md` :
un modèle a été entraîné, validé et rejeté avant qu'on s'aperçoive que le marché
lui-même ne bougeait jamais assez, en une barre, pour payer un aller-retour. La
mesure faite ici est celle qu'il aurait fallu faire AVANT d'entraîner quoi que ce
soit.

Propriété centrale : `tradable_window_ratio` est un PLAFOND. Il suppose la
direction connue d'avance et le timing parfait. Un modèle réel fait
nécessairement moins. Un plafond à zéro réfute donc l'horizon sans qu'aucun
modèle n'ait besoin d'être entraîné.

Domaine pur : aucune dépendance broker, aucun I/O.
"""

from __future__ import annotations

from typing import Sequence

from aegis_trade.domain.costs import TransactionCostModel


def absolute_moves(prices: Sequence[float], horizon: int) -> list[float]:
    """Mouvements absolus en fraction du prix, sur fenêtres glissantes.

    :param horizon: Nombre de barres de détention. Doit être >= 1.
    :raises ValueError: horizon non positif, prix insuffisants, ou prix non
        strictement positif (un prix nul ou négatif rend le rendement indéfini,
        et le laisser passer produirait une division silencieusement fausse).
    """
    if horizon < 1:
        raise ValueError(f"horizon doit être >= 1 (reçu {horizon}).")
    if len(prices) <= horizon:
        raise ValueError(
            f"{len(prices)} prix pour un horizon de {horizon} : "
            "aucune fenêtre complète, mesure impossible."
        )

    moves: list[float] = []
    for i in range(len(prices) - horizon):
        start = prices[i]
        if start <= 0.0:
            raise ValueError(f"Prix non strictement positif à l'indice {i} : {start}.")
        moves.append(abs((prices[i + horizon] / start) - 1.0))
    return moves


def tradable_window_ratio(
    prices: Sequence[float],
    horizon: int,
    cost_model: TransactionCostModel,
    safety_margin: float = 1.0,
) -> float:
    """Part des fenêtres où le mouvement réalisé couvre un aller-retour.

    Borne SUPÉRIEURE de ce qu'une stratégie peut capter à cet horizon : la
    direction est supposée connue. Un modèle réel reste sous cette borne.

    Retourne une valeur dans [0, 1]. Zéro signifie que l'horizon est réfuté :
    même un oracle y perdrait de l'argent.
    """
    threshold = cost_model.breakeven_return(safety_margin=safety_margin)
    moves = absolute_moves(prices, horizon)
    return sum(1 for move in moves if move >= threshold) / len(moves)


def is_horizon_tradable(
    prices: Sequence[float],
    horizon: int,
    cost_model: TransactionCostModel,
    min_ratio: float,
    safety_margin: float = 1.0,
) -> bool:
    """Verdict binaire : l'horizon laisse-t-il assez d'espace économique ?

    `min_ratio` est explicite et sans valeur par défaut : le seuil d'occasions
    acceptable dépend de la fréquence visée, et un défaut posé ici deviendrait
    une constante arbitraire de plus — exactement le défaut corrigé par
    l'ADR 0018 sur les seuils d'entrée.
    """
    if not 0.0 < min_ratio <= 1.0:
        raise ValueError(f"min_ratio doit être dans ]0, 1] (reçu {min_ratio}).")
    return tradable_window_ratio(prices, horizon, cost_model, safety_margin) >= min_ratio
