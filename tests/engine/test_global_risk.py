import pytest
from decimal import Decimal
from datetime import datetime, timezone
from aegis_trade.domain import Symbol, AssetClass
from aegis_trade.engine.events import OrderEvent, OrderAction
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import Portfolio

@pytest.fixture
def portfolio():
    return Portfolio(initial_capital=10000.0)

@pytest.fixture
def risk_manager():
    return GlobalRiskManager(
        max_gross_exposure=Decimal("1.0"),
        max_drawdown=Decimal("0.05"),
        max_concentration=Decimal("0.20")
    )

def _create_order(symbol_name: str, action: OrderAction, volume: float) -> OrderEvent:
    return OrderEvent(
        timestamp=datetime.now(timezone.utc),
        symbol=Symbol(symbol_name, AssetClass.FOREX),
        action=action,
        volume=Decimal(str(volume))
    )

def test_risk_manager_accepts_valid_order(portfolio, risk_manager):
    order = _create_order("EURUSD", OrderAction.BUY, 1.0)
    # Price is 1.0, equity is 10000. 1.0 / 10000 = 0.0001 (0.01% concentration)
    latest_prices = {Symbol("EURUSD", AssetClass.FOREX): Decimal("1.0")}
    
    approved, reason = risk_manager.validate_order(order, portfolio, latest_prices)
    assert approved is True
    assert reason == ""

def test_risk_manager_rejects_max_concentration(portfolio, risk_manager):
    # 20% limit of 10000 = 2000. 
    # Order volume 3000 * 1.0 = 3000 -> Should reject
    order = _create_order("EURUSD", OrderAction.BUY, 3000.0)
    latest_prices = {Symbol("EURUSD", AssetClass.FOREX): Decimal("1.0")}
    
    approved, reason = risk_manager.validate_order(order, portfolio, latest_prices)
    assert approved is False
    assert "Concentration" in reason

def test_risk_manager_rejects_max_gross_exposure(portfolio, risk_manager):
    # 100% limit of 10000 = 10000
    # Current portfolio holds 9000 EURUSD
    # Order volume 2000 USDJPY * 1.0 = 2000 -> Total = 11000 -> Should reject
    # First inject a position manually for the test
    portfolio._positions[Symbol("EURUSD", AssetClass.FOREX)] = type("Pos", (), {"volume": Decimal("9000"), "symbol": Symbol("EURUSD", AssetClass.FOREX)})()
    latest_prices = {
        Symbol("EURUSD", AssetClass.FOREX): Decimal("1.0"),
        Symbol("USDJPY", AssetClass.FOREX): Decimal("1.0")
    }
    
    order = _create_order("USDJPY", OrderAction.BUY, 2000.0)
    approved, reason = risk_manager.validate_order(order, portfolio, latest_prices)
    assert approved is False
    assert "Gross Exposure" in reason

def test_risk_manager_kill_switch_max_drawdown(portfolio, risk_manager):
    # Initial 10000. If it drops to 9400 (6% drawdown), reject opening.
    portfolio.equity = Decimal("9400.0")
    portfolio._equity_curve = [type("Point", (), {"equity": Decimal("10000.0")})()]
    
    latest_prices = {Symbol("EURUSD", AssetClass.FOREX): Decimal("1.0")}
    order = _create_order("EURUSD", OrderAction.BUY, 100.0)
    
    approved, reason = risk_manager.validate_order(order, portfolio, latest_prices)
    assert approved is False
    assert "Kill Switch" in reason

def test_risk_manager_kill_switch_allows_closing(portfolio, risk_manager):
    # Initial 10000. Drops to 9400 (6% drawdown).
    # But order is CLOSING an existing position.
    portfolio.equity = Decimal("9400.0")
    portfolio._equity_curve = [type("Point", (), {"equity": Decimal("10000.0")})()]
    
    sym = Symbol("EURUSD", AssetClass.FOREX)
    portfolio._positions[sym] = type("Pos", (), {"volume": Decimal("100"), "symbol": sym})()
    
    # We are long 100, we want to SELL 100
    latest_prices = {sym: Decimal("1.0")}
    order = _create_order("EURUSD", OrderAction.SELL, 100.0)
    
    approved, reason = risk_manager.validate_order(order, portfolio, latest_prices)
    assert approved is True
    assert reason == ""
