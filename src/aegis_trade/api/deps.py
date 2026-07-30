from fastapi import Depends
import os
from decimal import Decimal
from aegis_trade.application.monitoring.engine import MonitoringEngine
from aegis_trade.application.dashboard.services import DashboardService
from aegis_trade.application.paper_trading.orchestrator import PaperTradingOrchestrator
from aegis_trade.infrastructure.paper.deriv_gateway import DerivGateway, LiveDerivGateway
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import PortfolioEngine
from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.infrastructure.rl.policy_checkpoint_store import PolicyCheckpointStore

# Global instance for the local API
_monitoring_engine = MonitoringEngine()
_dashboard_service = DashboardService(_monitoring_engine)

# Singleton Orchestrator setup
_orchestrator = None

def get_orchestrator() -> PaperTradingOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        # Check environment
        env = os.environ.get("AEGIS_ENV", "DEMO").upper()
        token = os.environ.get("DERIV_DEMO_TOKEN", "dummy")
        
        if env == "LIVE":
            gateway = LiveDerivGateway(token=token, i_understand_this_is_real_money=True)
        else:
            gateway = DerivGateway(token=token)
            
        policy_store = PolicyCheckpointStore(storage_dir="data/rl/checkpoints")
        risk_manager = GlobalRiskManager(max_drawdown=Decimal("0.05"))
        portfolio = PortfolioEngine(initial_capital=Decimal("1000.0"))
        
        council = MultiAgentCouncil(
            agents=[]
        )
        
        _orchestrator = PaperTradingOrchestrator(
            broker=gateway,
            feed=None, # Will be set if needed
            risk_manager=risk_manager,
            portfolio_engine=portfolio,
            event_publisher=lambda e: None,
            council=council,
            policy_store=policy_store
        )
    return _orchestrator

def get_monitoring_engine() -> MonitoringEngine:
    return _monitoring_engine

def get_dashboard_service() -> DashboardService:
    return _dashboard_service

