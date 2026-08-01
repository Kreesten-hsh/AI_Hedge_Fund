"""Point de passage obligatoire de tout ordre vers un broker.

Le RiskEngine a autorité absolue (CLAUDE.md) : aucun chemin de code ne doit
pouvoir router un ordre sans risk check. Cette classe est le seul objet qui
sait dire « oui » ; toute passerelle d'exécution la reçoit au constructeur et
ne peut donc pas être instanciée sans elle.

Elle vit dans `engine/` parce que ses trois dépendances (`OrderEvent`,
`GlobalRiskManager`, `Portfolio`) y vivent : la placer dans `application/` ou
`infrastructure/` créerait un axe de dépendance inversé de plus.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Protocol, TYPE_CHECKING

from aegis_trade.domain.core import Symbol
from aegis_trade.engine.events import OrderEvent
from aegis_trade.engine.global_risk import GlobalRiskManager

if TYPE_CHECKING:
    from aegis_trade.engine.portfolio import Portfolio


class OrderRejectedByRisk(Exception):
    """Refus explicite du RiskEngine.

    Levée plutôt que retournée : un appelant qui oublie de tester un booléen
    laisse passer l'ordre, un appelant qui oublie de rattraper une exception
    s'arrête bruyamment. Le second échec est le seul acceptable ici.
    """

    def __init__(self, order: OrderEvent, reason: str) -> None:
        self.order = order
        self.reason = reason
        super().__init__(
            f"RiskEngine a refusé {order.action.value.upper()} "
            f"{order.volume} {order.symbol.name} : {reason}"
        )


class PriceSource(Protocol):
    def get_latest_price(self, symbol: Symbol) -> Decimal | None: ...


class RiskGate:
    """Autorise ou refuse un ordre. Ne l'exécute jamais."""

    def __init__(self, risk_manager: GlobalRiskManager, portfolio: "Portfolio") -> None:
        self._risk_manager = risk_manager
        self._portfolio = portfolio

    @property
    def risk_manager(self) -> GlobalRiskManager:
        return self._risk_manager

    @property
    def portfolio(self) -> "Portfolio":
        return self._portfolio

    def resolve_prices(
        self,
        order: OrderEvent,
        latest_prices: Mapping[Symbol, Decimal] | None = None,
    ) -> dict[Symbol, Decimal]:
        """Complète la table de prix avec ce que le portefeuille connaît déjà.

        Un prix manquant n'est pas comblé par une valeur par défaut : le
        RiskEngine rejettera l'ordre avec « Missing or invalid price », ce qui
        est le comportement voulu — un ordre sans prix n'est pas évaluable.
        """
        prices: dict[Symbol, Decimal] = dict(latest_prices or {})
        if order.symbol not in prices:
            getter = getattr(self._portfolio, "get_latest_price", None)
            if callable(getter):
                known = getter(order.symbol)
                if known is not None:
                    prices[order.symbol] = known
        return prices

    def evaluate(
        self,
        order: OrderEvent,
        latest_prices: Mapping[Symbol, Decimal] | None = None,
    ) -> tuple[bool, str]:
        prices = self.resolve_prices(order, latest_prices)
        return self._risk_manager.validate_order(order, self._portfolio, prices)

    def authorize(
        self,
        order: OrderEvent,
        latest_prices: Mapping[Symbol, Decimal] | None = None,
    ) -> None:
        """Laisse passer, ou lève `OrderRejectedByRisk`."""
        approved, reason = self.evaluate(order, latest_prices)
        if not approved:
            raise OrderRejectedByRisk(order, reason)
