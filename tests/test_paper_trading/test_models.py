import pytest
from decimal import Decimal
from datetime import datetime, timezone
from aegis_trade.domain import Symbol, AssetClass
from aegis_trade.domain.paper.models import PaperOrder, OrderType, ActionType
from aegis_trade.infrastructure.paper.models import (
    ConstantSlippageModel, SpreadSlippageModel, 
    FixedCommissionModel, PercentageCommissionModel
)

@pytest.fixture
def dummy_buy_order():
    return PaperOrder(
        order_id="O1",
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=ActionType.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("10.0"),
        timestamp=datetime.now(timezone.utc)
    )

@pytest.fixture
def dummy_sell_order():
    return PaperOrder(
        order_id="O2",
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=ActionType.SELL,
        order_type=OrderType.MARKET,
        volume=Decimal("10.0"),
        timestamp=datetime.now(timezone.utc)
    )

def test_constant_slippage(dummy_buy_order, dummy_sell_order):
    model = ConstantSlippageModel(Decimal("0.05"))
    assert model.calculate_slippage(dummy_buy_order, Decimal("100.0")) == Decimal("0.05")
    assert model.calculate_slippage(dummy_sell_order, Decimal("100.0")) == Decimal("-0.05")

def test_spread_slippage(dummy_buy_order, dummy_sell_order):
    model = SpreadSlippageModel(Decimal("0.01")) # 1% spread
    assert model.calculate_slippage(dummy_buy_order, Decimal("100.0")) == Decimal("0.5") # Half spread
    assert model.calculate_slippage(dummy_sell_order, Decimal("100.0")) == Decimal("-0.5")

def test_fixed_commission(dummy_buy_order):
    model = FixedCommissionModel(Decimal("1.50"))
    assert model.calculate_commission(dummy_buy_order, Decimal("100.0")) == Decimal("1.50")

def test_percentage_commission(dummy_buy_order):
    model = PercentageCommissionModel(Decimal("0.001")) # 0.1%
    assert model.calculate_commission(dummy_buy_order, Decimal("100.0")) == Decimal("1.0") # 10 shares * 100 = 1000 * 0.001 = 1.0
