import asyncio
import random
from decimal import Decimal
from aegis_trade.application.paper_trading.interfaces import ISlippageModel, ILatencyModel, ICommissionModel
from aegis_trade.domain.paper.models import PaperOrder, ActionType


class ConstantSlippageModel(ISlippageModel):
    def __init__(self, slippage_amount: Decimal):
        self.slippage_amount = slippage_amount

    def calculate_slippage(self, order: PaperOrder, market_price: Decimal) -> Decimal:
        """Returns the slippage amount to apply to the price. Positive for Buy, Negative for Sell."""
        if order.action == ActionType.BUY:
            return self.slippage_amount
        return -self.slippage_amount


class SpreadSlippageModel(ISlippageModel):
    def __init__(self, spread_percentage: Decimal):
        self.spread_percentage = spread_percentage

    def calculate_slippage(self, order: PaperOrder, market_price: Decimal) -> Decimal:
        """Calculates slippage as a percentage of the market price (half of the spread)."""
        slippage = market_price * (self.spread_percentage / Decimal("2.0"))
        if order.action == ActionType.BUY:
            return slippage
        return -slippage


class ConstantLatencyModel(ILatencyModel):
    def __init__(self, latency_ms: float):
        self.latency_ms = latency_ms

    async def simulate_latency(self) -> float:
        await asyncio.sleep(self.latency_ms / 1000.0)
        return self.latency_ms


class RandomLatencyModel(ILatencyModel):
    def __init__(self, min_ms: float, max_ms: float):
        self.min_ms = min_ms
        self.max_ms = max_ms

    async def simulate_latency(self) -> float:
        latency = random.uniform(self.min_ms, self.max_ms)
        await asyncio.sleep(latency / 1000.0)
        return latency


class FixedCommissionModel(ICommissionModel):
    def __init__(self, flat_fee: Decimal):
        self.flat_fee = flat_fee

    def calculate_commission(self, order: PaperOrder, fill_price: Decimal) -> Decimal:
        return self.flat_fee


class PercentageCommissionModel(ICommissionModel):
    def __init__(self, percentage: Decimal):
        self.percentage = percentage

    def calculate_commission(self, order: PaperOrder, fill_price: Decimal) -> Decimal:
        notional_value = fill_price * order.volume
        return notional_value * self.percentage
