import logging
from typing import List
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from aegis_trade.domain.paper.models import PaperExecutionReport

logger = logging.getLogger(__name__)

@dataclass
class ShadowTradeRecord:
    symbol: str
    action: str
    observed_price: Decimal
    executed_price: Decimal
    slippage_bps: float
    latency_ms: float
    timestamp: datetime

class ShadowTradingEngine:
    """
    Compares market observation prices with actual execution prices 
    to build an empirical slippage model.
    """
    def __init__(self):
        self.records: List[ShadowTradeRecord] = []
        
    def record_execution(self, observed_price: Decimal, report: PaperExecutionReport):
        if not report.execution:
            logger.warning(f"No execution data found in report {report.order.order_id}")
            return
            
        executed_price = report.execution.execution_price
        action = report.order.action.value.upper()
        
        if observed_price <= 0:
            return
            
        if action == "BUY":
            slippage = executed_price - observed_price
        else:
            slippage = observed_price - executed_price
            
        slippage_bps = float(slippage / observed_price) * 10000
        
        record = ShadowTradeRecord(
            symbol=report.order.symbol.name,
            action=action,
            observed_price=observed_price,
            executed_price=executed_price,
            slippage_bps=slippage_bps,
            latency_ms=report.execution.latency_ms,
            timestamp=report.execution.timestamp
        )
        self.records.append(record)
        logger.info(
            f"Shadow Trade Logged: {record.symbol} {record.action} | "
            f"Obs: {record.observed_price} | Exec: {record.executed_price} | "
            f"Slippage: {record.slippage_bps:.2f} bps | Latency: {record.latency_ms}ms"
        )
        
    def get_average_slippage(self) -> float:
        if not self.records:
            return 0.0
        return sum(r.slippage_bps for r in self.records) / len(self.records)
