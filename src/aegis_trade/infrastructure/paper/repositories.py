from typing import Optional, Dict
from aegis_trade.application.paper_trading.interfaces import IExecutionReportRepository
from aegis_trade.domain.paper.models import PaperExecutionReport


class MemoryExecutionRepository(IExecutionReportRepository):
    def __init__(self):
        self._reports: Dict[str, PaperExecutionReport] = {}

    def save(self, report: PaperExecutionReport) -> None:
        self._reports[report.order.order_id] = report

    def get_by_order_id(self, order_id: str) -> Optional[PaperExecutionReport]:
        return self._reports.get(order_id)
