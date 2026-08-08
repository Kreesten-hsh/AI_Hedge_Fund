"""Features réelles pour le Council, dérivées du flux de marché observé.

Avant ce module, l'orchestrateur injectait des constantes dont aucune ne
correspondait aux clés lues par les agents. Le Council ne pouvait donc voter
que WAIT, et `create_order` ne pouvait retourner que None : aucun ordre
n'était atteignable, quel que soit le marché.

Ce fournisseur ne calcule aucun indicateur lui-même : il délègue à
`IFeatureExtractor`. Recalculer un RSI ou une EMA ici ajouterait une
implémentation de plus à celles que le Lot 3 doit unifier.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Dict, Final, Mapping

from aegis_trade.domain.core import MarketBar, Symbol, Tick
from aegis_trade.domain.ports.features import IFeatureExtractor

# Clés lues par les agents (à gauche) et nom produit par l'extracteur (à
# droite). Le nom lu par les agents est le contrat : la traduction se fait ici,
# en un seul endroit, plutôt que dans cinq agents.
AGENT_FEATURE_SOURCES: Final[Mapping[str, str]] = {
    "ema_50": "ema_50",  # TrendAgent
    "rsi": "rsi_14",  # MomentumAgent
    "bb_upper": "bb_upper",  # VolatilityAgent
    "bb_lower": "bb_lower",  # VolatilityAgent
    "bb_middle": "bb_middle",
    "atr": "atr_14",  # écrit dans le contexte du trade, relu par la réflexion
}

# 200 barres : ce que demande la plus longue moyenne de l'extracteur (EMA 200).
DEFAULT_WINDOW: Final[int] = 200


class RollingFeatureProvider:
    """Maintient une fenêtre glissante par symbole et en dérive les features.

    Le calcul est refait sur toute la fenêtre à chaque barre. C'est un coût
    assumé : l'extracteur est la seule autorité sur les indicateurs, et un
    calcul incrémental parallèle divergerait de lui au premier écart d'arrondi.
    """

    def __init__(
        self,
        extractor: IFeatureExtractor,
        window: int = DEFAULT_WINDOW,
    ) -> None:
        if window < 1:
            raise ValueError("La fenêtre doit contenir au moins une barre.")
        self._extractor = extractor
        self._window = window
        self._bars: Dict[Symbol, deque[MarketBar]] = {}
        self._features: Dict[Symbol, Dict[str, float]] = {}
        self._spreads: Dict[Symbol, float] = {}
        self._latency_ms: float | None = None

    def observe_bar(self, bar: MarketBar) -> Dict[str, float]:
        """Ajoute une barre à l'historique et renvoie les features à jour."""
        history = self._bars.setdefault(bar.symbol, deque(maxlen=self._window))
        history.append(bar)
        features = self._compute(bar, history)
        self._features[bar.symbol] = features
        return features

    def observe_tick(self, tick: Tick) -> None:
        """Enregistre le spread réel d'une cotation.

        `MarketBar` ne porte pas de bid/ask : sans tick observé, le spread
        n'est pas publié plutôt que fabriqué à partir du bar.
        """
        self._spreads[tick.symbol] = float(tick.ask - tick.bid)

    def observe_latency(self, latency_ms: float) -> None:
        """Enregistre une latence broker réellement mesurée sur une exécution."""
        self._latency_ms = latency_ms

    def features_for(self, symbol: Symbol) -> Dict[str, float]:
        """Dernières features connues, ou dictionnaire vide si aucun tick."""
        return dict(self._features.get(symbol, {}))

    def history_size(self, symbol: Symbol) -> int:
        return len(self._bars.get(symbol, ()))

    def _compute(
        self, bar: MarketBar, history: deque[MarketBar]
    ) -> Dict[str, float]:
        extracted = self._extractor.extract(list(history))
        raw = extracted[-1].features if extracted else {}

        features: Dict[str, float] = {}
        for agent_key, source_key in AGENT_FEATURE_SOURCES.items():
            value = raw.get(source_key)
            # Une valeur indéfinie (chauffe des fenêtres glissantes) est omise,
            # pas mise à zéro : un bb_upper à 0.0 placerait le prix au-dessus
            # de la bande et ferait voter SELL sur une bande inexistante.
            if value is None:
                continue
            numeric = float(value)
            if math.isnan(numeric) or math.isinf(numeric):
                continue
            features[agent_key] = numeric

        # Le volume vient du bar lui-même : c'est une donnée observée, pas un
        # indicateur à dériver.
        features["volume"] = float(bar.volume)

        spread = self._spreads.get(bar.symbol)
        if spread is not None:
            features["spread"] = spread

        if self._latency_ms is not None:
            features["broker_latency_ms"] = self._latency_ms

        return features
