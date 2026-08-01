from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Awaitable, Callable, Optional, Protocol

from aegis_trade.domain.core import Symbol
from aegis_trade.domain.ports.broker import IExecutionGateway
from aegis_trade.engine.events import (
    FillEvent,
    OrderAction,
    OrderEvent,
    OrderLifecycleEvent,
)
from aegis_trade.engine.risk_gate import RiskGate


class FillSink(Protocol):
    """Destinataire des fills live : le `Portfolio` en production."""

    def on_fill_event(self, event: FillEvent) -> None: ...


class SymbolMapper(Protocol):
    def to_vnpy_symbol(self, symbol: Symbol) -> str: ...

    def from_vnpy_symbol(self, vnpy_symbol: str) -> Symbol: ...


class VnPyExecutionGateway(IExecutionGateway):
    def __init__(
        self,
        main_engine: Any,
        event_publisher: Callable[[Any], Awaitable[None]],
        symbol_mapper: SymbolMapper,
        risk_gate: Optional[RiskGate] = None,
        portfolio: Optional[FillSink] = None,
        max_remembered_trades: int = 10_000,
    ):
        self.main_engine = main_engine
        self.event_publisher = event_publisher
        self.symbol_mapper = symbol_mapper
        # Voir VnpyAdapter : pas de porte de risque, pas de routage.
        self.risk_gate = risk_gate
        # Destinataire des fills. Peut rester None quand la passerelle n'est
        # utilisée que pour router (tests d'autorité du RiskEngine) ; dans ce
        # cas `on_trade` publie l'événement sans l'appliquer nulle part.
        self.portfolio = portfolio
        # Un broker peut répéter un EVENT_TRADE (reconnexion, resynchro). Un
        # fill appliqué deux fois double la position dans le Portfolio, donc
        # l'exposition sur laquelle le RiskEngine décide.
        self._applied_trade_ids: set[str] = set()
        # Borne mémoire : une passerelle live tourne des semaines. La fenêtre
        # ne protège que contre les répétitions rapprochées (une resynchro
        # rejoue les fills récents), pas contre un rejeu très ancien.
        self._applied_trade_order: deque[str] = deque()
        self._max_remembered_trades = max_remembered_trades

    async def send_order(self, order: OrderEvent, latest_prices: Optional[dict] = None):
        """
        Translates an Aegis OrderEvent into a vn.py OrderRequest and sends it.

        Lève `OrderRejectedByRisk` si le RiskEngine refuse, `RuntimeError` si
        aucune porte de risque n'a été injectée.
        """
        if self.risk_gate is None:
            raise RuntimeError(
                "VnPyExecutionGateway sans RiskGate : aucun ordre ne peut être "
                "routé. Injecter un RiskGate à la construction."
            )
        self.risk_gate.authorize(order, latest_prices)

        from vnpy.trader.object import OrderRequest, Direction, OrderType

        # Translate OrderAction
        direction = Direction.LONG if order.action.value == "buy" else Direction.SHORT

        # Translate Symbol
        vt_symbol = self.symbol_mapper.to_vnpy_symbol(order.symbol)
        symbol, exchange = vt_symbol.split(".")
        from vnpy.trader.constant import Exchange
        try:
            exchange_enum = Exchange(exchange)
        except ValueError:
            # Fallback to a default if not strictly matched in vnpy constants
            exchange_enum = Exchange.LOCAL

        # Build OrderRequest
        req = OrderRequest(
            symbol=symbol,
            exchange=exchange_enum,
            direction=direction,
            type=OrderType.MARKET if order.order_type == "market" else OrderType.LIMIT,
            volume=float(order.volume),
            price=0.0, # Market order
            reference="AegisOS"
        )

        # Send via MainEngine
        # Assume self.gateway_name is configured or we use default
        gateway_name = exchange # simplification
        vt_orderid = self.main_engine.send_order(req, gateway_name)

        # Publish Submitted Event immediately
        event = OrderLifecycleEvent(
            order_id=vt_orderid,
            status="submitted",
            timestamp=datetime.now(timezone.utc)
        )
        await self.event_publisher(event)

    async def on_order(self, order):
        """
        Callback from vn.py for EVENT_ORDER.
        Translates back to Aegis OrderLifecycleEvent.
        """
        event = OrderLifecycleEvent(
            order_id=order.vt_orderid,
            status=order.status.value,
            timestamp=datetime.now(timezone.utc)
        )
        await self.event_publisher(event)

    async def on_trade(self, trade: Any) -> Optional[FillEvent]:
        """Callback vn.py EVENT_TRADE : le fill live alimente le Portfolio.

        Sans cette traduction, un ordre exécuté chez le broker n'existait pas
        côté Aegis : la position restait vide, donc l'equity ne bougeait pas,
        donc le drawdown restait nul et le kill switch ne pouvait jamais
        s'armer. C'est la boucle de retour qui rend le risque mesurable.

        Renvoie le `FillEvent` produit, ou None si le fill est un doublon.
        """
        fill = self._to_fill_event(trade)

        trade_id = self._trade_identity(trade)
        if trade_id in self._applied_trade_ids:
            # Doublon : ni appliqué, ni republié. Le republier ferait compter
            # deux fois le même fill par tout consommateur du bus (monitoring,
            # audit, P&L), ce qui reproduirait en aval le bug évité ici.
            return None
        self._remember_trade(trade_id)

        if self.portfolio is not None:
            self.portfolio.on_fill_event(fill)

        await self.event_publisher(fill)
        return fill

    def _remember_trade(self, trade_id: str) -> None:
        """Enregistre un fill comme appliqué, en gardant la mémoire bornée."""
        self._applied_trade_ids.add(trade_id)
        self._applied_trade_order.append(trade_id)
        while len(self._applied_trade_order) > self._max_remembered_trades:
            self._applied_trade_ids.discard(self._applied_trade_order.popleft())

    def _to_fill_event(self, trade: Any) -> FillEvent:
        """Traduit un `TradeData` vn.py en `FillEvent` du domaine.

        Toute valeur absente ou invalide fait échouer la traduction plutôt que
        de produire un fill approximatif : un prix ou un volume faux corrompt
        le P&L de façon irrécupérable.
        """
        symbol = self.symbol_mapper.from_vnpy_symbol(self._vt_symbol(trade))
        action = self._action_of(trade)
        timestamp = self._utc_timestamp(trade)

        return FillEvent(
            timestamp=timestamp,
            symbol=symbol,
            action=action,
            volume=Decimal(str(trade.volume)),
            fill_price=Decimal(str(trade.price)),
            # vn.py ne transporte pas la commission dans TradeData. Elle est
            # laissée à zéro et non estimée : une commission inventée fausse le
            # P&L exactement comme un prix inventé.
            commission=Decimal("0.0"),
            exchange=self._exchange_of(trade),
            strategy_id=getattr(trade, "reference", "") or "vnpy_live",
        )

    def _vt_symbol(self, trade: Any) -> str:
        vt_symbol = getattr(trade, "vt_symbol", None)
        if isinstance(vt_symbol, str) and vt_symbol:
            return vt_symbol
        symbol = getattr(trade, "symbol", None)
        if isinstance(symbol, str) and symbol:
            return symbol
        raise ValueError("TradeData sans symbole exploitable : fill non traduisible.")

    def _action_of(self, trade: Any) -> OrderAction:
        """Sens du fill.

        Une direction absente n'est pas assimilée à un achat : traiter un fill
        de sens inconnu comme un BUY inverserait le signe de la position.
        """
        direction = getattr(trade, "direction", None)
        raw = getattr(direction, "name", None) or str(direction or "")
        upper = raw.upper()
        if "LONG" in upper:
            return OrderAction.BUY
        if "SHORT" in upper:
            return OrderAction.SELL
        raise ValueError(
            f"Direction vn.py non reconnue ({direction!r}) : le sens du fill "
            f"doit être explicite, il détermine le signe de la position."
        )

    def _exchange_of(self, trade: Any) -> str:
        exchange = getattr(trade, "exchange", None)
        value = getattr(exchange, "value", None)
        if isinstance(value, str) and value:
            return value
        return str(exchange) if exchange is not None else "UNKNOWN"

    def _utc_timestamp(self, trade: Any) -> datetime:
        """Horodatage du fill, ramené en UTC.

        `EngineEvent` refuse tout timestamp naïf ou non-UTC. vn.py livre
        l'heure locale du gateway : une datetime naïve est donc interprétée
        comme UTC plutôt que rejetée, faute de fuseau transmis par le broker.
        """
        moment = getattr(trade, "datetime", None)
        if not isinstance(moment, datetime):
            return datetime.now(timezone.utc)
        if moment.tzinfo is None:
            return moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc)

    def _trade_identity(self, trade: Any) -> str:
        """Identité stable d'un fill, pour la déduplication."""
        for attribute in ("vt_tradeid", "tradeid"):
            value = getattr(trade, attribute, None)
            if isinstance(value, str) and value:
                return value
        raise ValueError(
            "TradeData sans identifiant de trade : impossible de garantir "
            "qu'un fill ne sera pas appliqué deux fois au Portfolio."
        )
