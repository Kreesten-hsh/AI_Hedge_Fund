from typing import List, Dict, Any
from aegis_trade.application.monitoring.engine import MonitoringEngine
from aegis_trade.application.monitoring.models import (
    PortfolioSnapshot, RiskSnapshot, SystemSnapshot, PerformanceSnapshot
)

class DashboardService:
    def __init__(self, monitoring_engine: MonitoringEngine):
        self.monitoring = monitoring_engine

    def get_portfolio_status(self) -> PortfolioSnapshot:
        return self.monitoring.portfolio

    def get_risk_status(self) -> RiskSnapshot:
        return self.monitoring.risk

    def get_system_health(self) -> SystemSnapshot:
        return self.monitoring.system

    def get_performance_metrics(self) -> PerformanceSnapshot:
        return self.monitoring.performance
