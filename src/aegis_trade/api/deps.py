from fastapi import Depends
from aegis_trade.application.monitoring.engine import MonitoringEngine
from aegis_trade.application.dashboard.services import DashboardService

# Global instance for the local API
_monitoring_engine = MonitoringEngine()
_dashboard_service = DashboardService(_monitoring_engine)

def get_monitoring_engine() -> MonitoringEngine:
    return _monitoring_engine

def get_dashboard_service() -> DashboardService:
    return _dashboard_service
