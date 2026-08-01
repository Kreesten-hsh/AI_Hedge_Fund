"""Port d'entrée des données de marché temps réel.

Le domaine ne connaît que `Tick`. Aucune implémentation de ce port ne doit
faire remonter un objet de bibliothèque tierce (message WebSocket, DataFrame,
dictionnaire JSON) au-delà de sa propre frontière.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from aegis_trade.domain.core import Symbol, Tick


class IMarketDataGateway(ABC):
    """Flux de ticks pour un ou plusieurs symboles."""

    @abstractmethod
    async def connect(self) -> None:
        """Ouvre la session. Lève si la session ne peut pas être établie."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Ferme la session. Idempotent."""

    @abstractmethod
    async def subscribe(self, symbol: Symbol) -> None:
        """Demande la diffusion des ticks de `symbol`."""

    @abstractmethod
    def stream(self) -> AsyncIterator[Tick]:
        """Ticks des symboles souscrits, dans l'ordre d'arrivée.

        Le flux s'arrête quand la session se ferme. Il ne produit jamais de
        valeur inventée en cas de silence du broker : un flux muet reste muet,
        de sorte qu'une panne de données ne ressemble jamais à un marché calme.
        """
