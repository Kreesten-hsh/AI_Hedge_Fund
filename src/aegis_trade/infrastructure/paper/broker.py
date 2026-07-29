import asyncio
from datetime import datetime, timezone
import uuid
from decimal import Decimal
from typing import Callable, Awaitable

from aegis_trade.application.paper_trading.interfaces import (
    IPaperBroker, ISlippageModel, ILatencyModel, ICommissionModel, IExecutionReportRepository
)
from aegis_trade.domain.paper.models import (
    PaperOrder, OrderState, PaperExecutionReport, PaperExecution, PaperFill,
    PaperAccount, ActionType, PaperPosition
)
from aegis_trade.engine.events import OrderLifecycleEvent, PositionEvent, AccountEvent


class PaperBroker(IPaperBroker):
    def __init__(
        self,
        account: PaperAccount,
        slippage_model: ISlippageModel,
        latency_model: ILatencyModel,
        commission_model: ICommissionModel,
        repository: IExecutionReportRepository,
        event_publisher: Callable[[any], Awaitable[None]]
    ):
        self.account = account
        self.slippage_model = slippage_model
        self.latency_model = latency_model
        self.commission_model = commission_model
        self.repository = repository
        self.event_publisher = event_publisher
        
        # A mock current market price for limit/stop simulations.
        # In a real system, the broker reads from the feed.
        self._current_market_price = Decimal("100.0")

    def update_market_price(self, price: Decimal):
        self._current_market_price = price

    async def submit_order(self, order: PaperOrder) -> PaperExecutionReport:
        # 1. Recevoir et Valider
        if not order.can_transition_to(OrderState.SUBMITTED):
            return self._reject_order(order, "Invalid state transition to SUBMITTED")
            
        order = self._change_state(order, OrderState.SUBMITTED)
        await self._publish_lifecycle(order, "Order submitted to broker")

        # 2. Vérifier le portefeuille / marge (Basic validation)
        # Assuming we need enough balance for BUY orders.
        notional_value = order.volume * (order.limit_price or self._current_market_price)
        
        # NOTE: Full risk should be handled by GlobalRiskManager before reaching broker, 
        # but the broker does its own final margin sanity check.
        if order.action == ActionType.BUY and self.account.balances.get("USD"):
            if self.account.balances["USD"].available < notional_value:
                return self._reject_order(order, "Insufficient funds")

        order = self._change_state(order, OrderState.ACCEPTED)
        await self._publish_lifecycle(order, "Order accepted by broker")

        # 3. Simuler la latence
        latency = await self.latency_model.simulate_latency()

        # 4. Calculer le slippage et le prix d'exécution
        # For simplicity, simulating market order execution immediately.
        slippage = self.slippage_model.calculate_slippage(order, self._current_market_price)
        execution_price = self._current_market_price + slippage

        # 5. Calculer la commission
        commission = self.commission_model.calculate_commission(order, execution_price)

        # 6. Produire un Fill
        fill_id = str(uuid.uuid4())
        fill = PaperFill(
            fill_id=fill_id,
            order_id=order.order_id,
            symbol=order.symbol,
            action=order.action,
            volume=order.volume,
            price=execution_price,
            commission=commission,
            timestamp=datetime.now(timezone.utc)
        )

        execution = PaperExecution(
            execution_id=str(uuid.uuid4()),
            order_id=order.order_id,
            timestamp=fill.timestamp,
            requested_price=self._current_market_price,
            execution_price=execution_price,
            slippage=slippage,
            latency_ms=latency
        )

        # 7. Mettre à jour les positions (Account interne au broker)
        portfolio_before = self._calculate_portfolio_value()
        await self._apply_fill(fill)
        portfolio_after = self._calculate_portfolio_value()

        # Update order state
        order = self._change_state(order, OrderState.FILLED)
        order = object.__setattr__(order, 'filled_volume', order.volume) or order
        order = object.__setattr__(order, 'average_fill_price', execution_price) or order

        await self._publish_lifecycle(order, "Order filled")

        # 8. Journalisation
        report = PaperExecutionReport(
            timestamp=datetime.now(timezone.utc),
            order=order,
            risk_decision="APPROVED",
            execution=execution,
            fills=[fill],
            portfolio_value_before=portfolio_before,
            portfolio_value_after=portfolio_after
        )
        self.repository.save(report)
        return report

    async def cancel_order(self, order_id: str) -> bool:
        # Simplified for immediate execution
        return False

    def _reject_order(self, order: PaperOrder, reason: str) -> PaperExecutionReport:
        order = self._change_state(order, OrderState.REJECTED)
        asyncio.create_task(self._publish_lifecycle(order, f"Rejected: {reason}"))
        
        report = PaperExecutionReport(
            timestamp=datetime.now(timezone.utc),
            order=order,
            risk_decision=f"REJECTED: {reason}",
        )
        self.repository.save(report)
        return report

    def _change_state(self, order: PaperOrder, new_state: OrderState) -> PaperOrder:
        # Dataclass is frozen, we use object.__setattr__ to mutate safely or recreate.
        object.__setattr__(order, 'state', new_state)
        return order
        
    async def _publish_lifecycle(self, order: PaperOrder, message: str):
        event = OrderLifecycleEvent(
            timestamp=datetime.now(timezone.utc),
            order_id=order.order_id,
            status=order.state.value,
            message=message
        )
        await self.event_publisher(event)

    def _calculate_portfolio_value(self) -> Decimal:
        val = sum((b.total for b in self.account.balances.values()), Decimal("0.0"))
        # Simplified position valuation
        val += sum((p.volume * self._current_market_price for p in self.account.positions.values()), Decimal("0.0"))
        return val

    async def _apply_fill(self, fill: PaperFill):
        # Update balance
        if "USD" in self.account.balances:
            bal = self.account.balances["USD"]
            cost = (fill.volume * fill.price) + fill.commission
            if fill.action == ActionType.BUY:
                object.__setattr__(bal, 'total', bal.total - cost)
                object.__setattr__(bal, 'available', bal.available - cost)
            else:
                object.__setattr__(bal, 'total', bal.total + (fill.volume * fill.price) - fill.commission)
                object.__setattr__(bal, 'available', bal.available + (fill.volume * fill.price) - fill.commission)
                
            await self.event_publisher(AccountEvent(
                timestamp=datetime.now(timezone.utc),
                account_id=self.account.account_id,
                action="balance_updated",
                currency="USD",
                amount=bal.total
            ))

        # Update position
        if fill.symbol not in self.account.positions:
            self.account.positions[fill.symbol] = PaperPosition(symbol=fill.symbol, volume=Decimal("0.0"), average_price=Decimal("0.0"))
        
        pos = self.account.positions[fill.symbol]
        if fill.action == ActionType.BUY:
            new_volume = pos.volume + fill.volume
            new_avg = ((pos.volume * pos.average_price) + (fill.volume * fill.price)) / new_volume if new_volume > 0 else Decimal("0.0")
        else:
            new_volume = pos.volume - fill.volume
            new_avg = pos.average_price # Simplified avg cost closing
            
        object.__setattr__(pos, 'volume', new_volume)
        object.__setattr__(pos, 'average_price', new_avg)
        
        await self.event_publisher(PositionEvent(
            timestamp=datetime.now(timezone.utc),
            symbol=fill.symbol,
            action="opened" if new_volume == fill.volume else "updated",
            volume=new_volume,
            average_price=new_avg
        ))
