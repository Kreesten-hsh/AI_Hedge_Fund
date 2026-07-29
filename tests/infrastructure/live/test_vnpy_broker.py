import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from decimal import Decimal

from aegis_trade.domain.core import Symbol
from aegis_trade.engine.events import OrderEvent, OrderAction, MarketEvent, OrderLifecycleEvent
from aegis_trade.infrastructure.live.vnpy.mapper import VnPySymbolMapper
from aegis_trade.infrastructure.live.vnpy.market_data import VnPyMarketGateway
from aegis_trade.infrastructure.live.vnpy.execution import VnPyExecutionGateway
from aegis_trade.infrastructure.live.vnpy.broker import VnPyBroker
from aegis_trade.infrastructure.live.vnpy.manager import VnPyEngineManager


def test_mapper():
    mapper = VnPySymbolMapper("BINANCE")
    aegis_symbol = Symbol(name="BTCUSDT", asset_class="CRYPTO")
    vnpy_symbol = mapper.to_vnpy_symbol(aegis_symbol)
    assert vnpy_symbol == "BTCUSDT.BINANCE"
    
    back_to_aegis = mapper.from_vnpy_symbol(vnpy_symbol)
    assert back_to_aegis.name == "BTCUSDT"
    
    with pytest.raises(ValueError):
        mapper.from_vnpy_symbol("")

@pytest.mark.asyncio
async def test_market_gateway():
    publisher = AsyncMock()
    mapper = VnPySymbolMapper("BINANCE")
    gateway = VnPyMarketGateway(publisher, mapper)
    
    mock_tick = Mock()
    mock_tick.vt_symbol = "BTCUSDT.BINANCE"
    mock_tick.last_price = 50000.0
    mock_tick.volume = 1.5
    
    await gateway.on_tick(mock_tick)
    
    publisher.assert_called_once()
    event = publisher.call_args[0][0]
    assert isinstance(event, MarketEvent)
    assert event.bar.symbol.name == "BTCUSDT"
    assert event.bar.close == Decimal("50000.0")

@pytest.mark.asyncio
async def test_execution_gateway():
    publisher = AsyncMock()
    mapper = VnPySymbolMapper("BINANCE")
    mock_engine = Mock()
    mock_engine.send_order.return_value = "vt_123"
    
    gateway = VnPyExecutionGateway(mock_engine, publisher, mapper)
    
    order = OrderEvent(
        symbol=Symbol(name="BTCUSDT", asset_class="CRYPTO"),
        timestamp=datetime.now(timezone.utc),
        action=OrderAction.BUY,
        volume=Decimal("1.0"),
        order_type="market"
    )
    
    await gateway.send_order(order)
    
    mock_engine.send_order.assert_called_once()
    publisher.assert_called_once()
    
    event = publisher.call_args[0][0]
    assert isinstance(event, OrderLifecycleEvent)
    assert event.order_id == "vt_123"
    assert event.status == "submitted"

def test_engine_manager():
    manager = VnPyEngineManager()
    assert manager.health_check() == "Disconnected"
    manager._is_connected = True
    assert manager.health_check() == "Connected"
    
def test_broker_facade():
    market = Mock()
    exec_gateway = Mock()
    broker = VnPyBroker(market, exec_gateway)
    assert broker.market_gateway == market
    assert broker.execution_gateway == exec_gateway
