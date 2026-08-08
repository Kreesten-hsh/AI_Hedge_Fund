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

import math
from typing import Sequence

from aegis_trade.domain.costs import TransactionCostModel


def _forward_returns(prices: Sequence[float], horizon: int) -> list[float]:
    """Rendements signés sur fenêtres glissantes, en fraction du prix.

    Primitive commune aux deux lectures d'un horizon : `absolute_moves` en jette
    le signe pour mesurer un péage (symétrique), l'oracle d'exposition le garde
    pour choisir un sens. Les deux partagent volontairement ce seul site de
    validation — dupliquer les gardes les ferait diverger en silence.
    """
    if horizon < 1:
        raise ValueError(f"horizon doit être >= 1 (reçu {horizon}).")
    if len(prices) <= horizon:
        raise ValueError(
            f"{len(prices)} prix pour un horizon de {horizon} : "
            "aucune fenêtre complète, mesure impossible."
        )

    returns: list[float] = []
    for i in range(len(prices) - horizon):
        start = prices[i]
        if start <= 0.0:
            raise ValueError(f"Prix non strictement positif à l'indice {i} : {start}.")
        returns.append((prices[i + horizon] / start) - 1.0)
    return returns


def absolute_moves(prices: Sequence[float], horizon: int) -> list[float]:
    """Mouvements absolus en fraction du prix, sur fenêtres glissantes.

    :param horizon: Nombre de barres de détention. Doit être >= 1.
    :raises ValueError: horizon non positif, prix insuffisants, ou prix non
        strictement positif (un prix nul ou négatif rend le rendement indéfini,
        et le laisser passer produirait une division silencieusement fausse).
    """
    return [abs(r) for r in _forward_returns(prices, horizon)]


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


def max_viable_round_trip_cost(
    prices: Sequence[float],
    horizon: int,
    min_ratio: float,
) -> float:
    """Coût aller-retour le plus élevé qui laisse encore `min_ratio` de fenêtres tradables.

    Inverse de `tradable_window_ratio` : au lieu de demander « ce coût laisse-t-il
    de la place ? », répond « quelle place reste-t-il, quel que soit le coût ? ».

    Motivation : le coût réel du broker peut être inconnu au moment où l'horizon
    cible se décide (les coûts Deriv sur indices synthétiques ne sont pas ceux du
    `SimulatedBroker`, cf. ADR 0018). Choisir un horizon à partir d'un coût
    supposé revient à construire la recherche sur un chiffre non mesuré. La borne
    retournée ici ne dépend d'aucune hypothèse de frais : le coût mesuré plus tard
    se compare simplement à elle.

    Retourne le quantile `1 - min_ratio` des mouvements absolus, en fraction du
    prix. Un coût strictement supérieur à cette valeur fait tomber la part de
    fenêtres tradables sous `min_ratio`.

    :param min_ratio: Part de fenêtres exigée, dans ]0, 1]. Sans valeur par
        défaut pour la même raison que `is_horizon_tradable` : la fréquence
        d'occasions acceptable dépend du style visé et n'est pas dérivable ici.
    """
    if not 0.0 < min_ratio <= 1.0:
        raise ValueError(f"min_ratio doit être dans ]0, 1] (reçu {min_ratio}).")

    moves = sorted(absolute_moves(prices, horizon), reverse=True)
    # `moves` est décroissant : le k-ième plus grand mouvement est le plus grand
    # coût que `k` fenêtres couvrent encore. `ceil` garantit que la part obtenue
    # atteint `min_ratio` au lieu de passer juste dessous par troncature.
    rank = min(math.ceil(len(moves) * min_ratio), len(moves))
    return moves[rank - 1]


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


def oracle_target_exposure(
    prices: Sequence[float],
    horizon: int,
    cost_model: TransactionCostModel,
    safety_margin: float = 1.0,
) -> list[int]:
    """Exposition cible qu'une `MLStrategy` déclarerait avec une prédiction parfaite.

    Reproduit exactement la règle de décision de
    `MLStrategy.generate_signals` : `>= +seuil` long (1), `<= -seuil` short (-1),
    entre les deux PLAT (0). La zone morte n'est pas un silence, c'est l'ordre de
    sortir — c'est ce qui rend la sortie dépendante de la persistance du signal
    plutôt que de l'horizon du label.

    Un élément par fenêtre complète : les `horizon` dernières barres n'ont pas de
    rendement futur, l'oracle n'y a donc aucun avis à porter.
    """
    threshold = cost_model.breakeven_return(safety_margin=safety_margin)
    exposure: list[int] = []
    for forward_return in _forward_returns(prices, horizon):
        if forward_return >= threshold:
            exposure.append(1)
        elif forward_return <= -threshold:
            exposure.append(-1)
        else:
            exposure.append(0)
    return exposure


def oracle_holding_periods(
    prices: Sequence[float],
    horizon: int,
    cost_model: TransactionCostModel,
    safety_margin: float = 1.0,
) -> list[int]:
    """Durées de détention, en barres, d'une sortie par persistance du signal.

    Répond à la question laissée ouverte par SIG-02 : « horizon du label » n'est
    pas « durée de détention ». `tradable_window_ratio` mesure une sortie
    TEMPORELLE — `absolute_moves` compare `t+horizon` à `t`, donc suppose la
    position fermée à la barre `t+horizon`. `MLStrategy` ne fait pas ça : elle
    réémet une exposition cible à chaque barre et sort quand le signal retombe
    dans la zone morte ou change de sens. La détention est donc la longueur des
    séquences d'exposition non nulle constante, mesurée ici.

    Chaque élément est une détention distincte, donc un aller-retour distinct.
    Une liste vide signifie qu'aucune position n'est jamais ouverte — pas qu'une
    position dure zéro barre.

    Ce que cette mesure EST : la structure de persistance du label lui-même,
    calculable sans entraîner quoi que ce soit. Ce qu'elle n'est PAS : une borne
    sur la détention d'un modèle réel. Le bruit de prédiction fragmente
    typiquement les séquences, mais peut aussi en souder deux — aucune
    inégalité n'est démontrée dans ce sens et aucune n'est revendiquée ici.
    """
    periods: list[int] = []
    current_side = 0
    current_length = 0

    for side in oracle_target_exposure(prices, horizon, cost_model, safety_margin):
        if side == current_side:
            current_length += 1
            continue
        # Changement de sens comme retour au plat : la position en cours se
        # ferme. Un passage long -> short est deux aller-retours, jamais une
        # détention continue.
        if current_side != 0:
            periods.append(current_length)
        current_side = side
        current_length = 1

    if current_side != 0:
        periods.append(current_length)
    return periods
