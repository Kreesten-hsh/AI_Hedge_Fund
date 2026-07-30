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

from aegis_trade.infrastructure.reasoning.knowledge_repo import InMemoryKnowledgeRepository
from aegis_trade.application.reasoning.llm_adapter import MockReasoner
from aegis_trade.application.reasoning.knowledge import KnowledgeGenerator
from aegis_trade.application.reasoning.clustering import DBSCANClusterEngine
from aegis_trade.application.reasoning.analyzer import ExperienceAnalyzer

from aegis_trade.application.council.agents.trend_agent import TrendAgent
from aegis_trade.application.council.agents.momentum_agent import MomentumAgent
from aegis_trade.application.council.agents.volatility_agent import VolatilityAgent
from aegis_trade.application.council.agents.liquidity_agent import LiquidityAgent
from aegis_trade.application.council.agents.pattern_agent import PatternAgent
from aegis_trade.application.council.agents.portfolio_agent import PortfolioAgent
from aegis_trade.application.council.agents.execution_agent import ExecutionAgent
from aegis_trade.application.council.agents.news_agent import NewsAgent

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
        
        # AI-03 Reasoning Dependencies
        knowledge_repo = InMemoryKnowledgeRepository()
        reasoner = MockReasoner()
        knowledge_generator = KnowledgeGenerator(reasoner=reasoner)
        cluster_engine = DBSCANClusterEngine()
        experience_analyzer = ExperienceAnalyzer()
        
        # Make these globally available via monitoring engine for post-trade async processing
        _monitoring_engine.knowledge_repo = knowledge_repo
        _monitoring_engine.knowledge_generator = knowledge_generator
        _monitoring_engine.cluster_engine = cluster_engine
        
        council = MultiAgentCouncil(
            agents=[
                TrendAgent(),
                MomentumAgent(),
                VolatilityAgent(),
                LiquidityAgent(),
                PatternAgent(knowledge_repo=knowledge_repo),
                PortfolioAgent(),
                ExecutionAgent(),
                NewsAgent()
            ]
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

