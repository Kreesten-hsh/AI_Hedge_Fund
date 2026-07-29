import abc
from decimal import Decimal
from typing import AsyncGenerator, Optional
from aegis_trade.domain import MarketBar
from aegis_trade.domain.paper.models import PaperOrder, PaperExecutionReport, PaperAccount


class ISlippageModel(abc.ABC):
    @abc.abstractmethod
    def calculate_slippage(self, order: PaperOrder, market_price: Decimal) -> Decimal:
        """Calculate slippage per unit of volume based on market conditions."""
        pass


class ILatencyModel(abc.ABC):
    @abc.abstractmethod
    async def simulate_latency(self) -> float:
        """Simulate latency and pause execution for that duration. Returns latency in ms."""
        pass


class ICommissionModel(abc.ABC):
    @abc.abstractmethod
    def calculate_commission(self, order: PaperOrder, fill_price: Decimal) -> Decimal:
        """Calculate the commission required for the transaction."""
        pass


class IExecutionSimulator(abc.ABC):
    @abc.abstractmethod
    async def execute_order(self, order: PaperOrder, account: PaperAccount) -> PaperExecutionReport:
        """Execute an order by evaluating slippage, commission, and latency."""
        pass


class IPaperBroker(abc.ABC):
    @abc.abstractmethod
    async def submit_order(self, order: PaperOrder) -> PaperExecutionReport:
        """Submit an order to the paper broker."""
        pass
        
    @abc.abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order."""
        pass


class IMarketFeed(abc.ABC):
    @abc.abstractmethod
    async def subscribe(self) -> AsyncGenerator[MarketBar, None]:
        """Subscribe to a stream of market data."""
        pass


class IExecutionReportRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, report: PaperExecutionReport) -> None:
        """Persist an execution report."""
        pass
        
    @abc.abstractmethod
    def get_by_order_id(self, order_id: str) -> Optional[PaperExecutionReport]:
        """Retrieve a report by its order ID."""
        pass
