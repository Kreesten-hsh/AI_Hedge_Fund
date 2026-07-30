import pytest
from decimal import Decimal
from datetime import datetime, timezone

from aegis_trade.domain.core import Symbol, AssetClass
from aegis_trade.domain.paper.models import PaperExecutionReport, PaperOrder, ActionType, OrderType, PaperExecution, OrderState
from aegis_trade.application.validation.shadow import ShadowTradingEngine

def test_shadow_trading_engine_calculates_slippage():
    engine = ShadowTradingEngine()
    
    # 10 bps slippage on 150.0 is 0.15, so execution is 150.15 for BUY
    order = PaperOrder(
        order_id="1",
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        action=ActionType.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("1.0"),
        timestamp=datetime.now(timezone.utc)
    )
    
    execution = PaperExecution(
        execution_id="E1",
        order_id="1",
        timestamp=datetime.now(timezone.utc),
        requested_price=Decimal("150.0"),
        execution_price=Decimal("150.15"),
        slippage=Decimal("0.15"),
        latency_ms=15.0
    )
    
    report = PaperExecutionReport(
        timestamp=datetime.now(timezone.utc),
        order=order,
        risk_decision="APPROVED",
        execution=execution
    )
    
    engine.record_execution(observed_price=Decimal("150.0"), report=report)
    
    assert len(engine.records) == 1
    # 150.15 - 150.00 = 0.15. 0.15 / 150.0 = 0.001. 0.001 * 10000 = 10 bps.
    assert engine.records[0].slippage_bps == 10.0
    
    assert engine.get_average_slippage() == 10.0
