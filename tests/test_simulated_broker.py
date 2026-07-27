import pytest
from datetime import datetime, timezone

from aegis_trade.domain.core import Symbol, AssetClass
from aegis_trade.domain.execution import OrderIntent
from aegis_trade.infrastructure.brokers.simulated_broker import SimulatedBroker

def test_simulated_broker_execution():
    broker = SimulatedBroker(commission_rate=0.001, slippage_bps=10.0)
    symbol = Symbol("BTCUSD", AssetClass.CRYPTO)
    
    # Test Long Order
    intent_long = OrderIntent(
        symbol=symbol,
        direction=1,
        quantity=1.0,
        target_price=100.0,
        timestamp=datetime.now(timezone.utc)
    )
    
    fill_long = broker.execute_order(intent_long)
    assert fill_long is not None
    # Slippage is 10 bps = 0.1% -> 100 * (1 + 0.001) = 100.1
    assert fill_long.fill_price == 100.1
    # Commission is 0.1% of trade value (100.1 * 1.0 = 100.1) -> 0.1001
    assert pytest.approx(fill_long.commission) == 0.1001
    
    # Test Short Order
    intent_short = OrderIntent(
        symbol=symbol,
        direction=-1,
        quantity=2.0,
        target_price=100.0,
        timestamp=datetime.now(timezone.utc)
    )
    
    fill_short = broker.execute_order(intent_short)
    assert fill_short is not None
    # Slippage works against trader: sell for less -> 100 * (1 - 0.001) = 99.9
    assert fill_short.fill_price == 99.9
    # Commission is 0.1% of (99.9 * 2 = 199.8) -> 0.1998
    assert pytest.approx(fill_short.commission) == 0.1998

def test_simulated_broker_zero_quantity():
    broker = SimulatedBroker()
    intent = OrderIntent(
        symbol=Symbol("BTCUSD", AssetClass.CRYPTO),
        direction=1,
        quantity=0.0,
        target_price=100.0,
        timestamp=datetime.now(timezone.utc)
    )
    assert broker.execute_order(intent) is None
