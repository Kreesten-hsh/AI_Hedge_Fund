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
from typing import Any, Mapping, Protocol, TYPE_CHECKING

from aegis_trade.domain.core import Symbol
from aegis_trade.engine.events import OrderEvent
from aegis_trade.engine.global_risk import GlobalRiskManager

if TYPE_CHECKING:
    from aegis_trade.engine.portfolio import Portfolio


RISK_DECISION_KEY = "risk_decision"
"""Clé sous laquelle la décision est inscrite dans `context_features`."""

RISK_DECISION_APPROVED = "APPROVED_BY_RISK_ENGINE"
"""Verdict d'approbation explicite.

`GlobalRiskManager.validate_order` renvoie `(True, "")` : le motif est vide
quand l'ordre passe. Recopier ce motif tel quel produirait une décision
indiscernable d'une décision absente, et un aval prudent la dégraderait en
« UNRECORDED ». Le jeton est donc posé ici, une seule fois, plutôt que réécrit
par chaque broker.
"""


RISK_DECISION_UNRECORDED = "UNRECORDED"
"""Verdict d'un ordre arrivé au broker sans trace de passage au RiskEngine.

Volontairement distinct d'un refus : le RiskEngine n'a rien dit, ce n'est donc
ni une approbation ni un rejet. Le rapport d'exécution doit pouvoir montrer
cette différence à l'audit.
"""


def recorded_decision(context_features: Mapping[Any, Any] | None) -> str:
    """Décision de risque réellement portée par un ordre.

    Un ordre sans trace exploitable est signalé `UNRECORDED`, jamais promu en
    approbation : c'est la seule façon qu'un contournement du RiskEngine reste
    visible dans le journal au lieu d'être maquillé.
    """
    if not context_features:
        return RISK_DECISION_UNRECORDED
    decision = context_features.get(RISK_DECISION_KEY)
    if isinstance(decision, str) and decision:
        return decision
    return RISK_DECISION_UNRECORDED


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
    ) -> str:
        """Laisse passer en renvoyant le verdict, ou lève `OrderRejectedByRisk`.

        Le verdict est retourné pour être inscrit dans l'ordre transmis au
        broker : sans cette trace, un broker ne peut que supposer que l'ordre a
        été validé, et une approbation écrite en dur côté broker survit même
        quand le check a été contourné.
        """
        approved, reason = self.evaluate(order, latest_prices)
        if not approved:
            raise OrderRejectedByRisk(order, reason)
        return RISK_DECISION_APPROVED
