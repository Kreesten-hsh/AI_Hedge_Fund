import pytest
from decimal import Decimal
from aegis_trade.domain.council import MarketContext, AgentVote, IVotingAgent
from aegis_trade.domain.rl import PolicyDecision
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.domain import Symbol
from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import PortfolioEngine

class MockAgent(IVotingAgent):
    def __init__(self, name: str, vote_direction: str, confidence: float):
        self._name = name
        self._vote_direction = vote_direction
        self._confidence = confidence

    @property
    def name(self) -> str:
        return self._name

    def vote(self, context: MarketContext) -> AgentVote:
        return AgentVote(self.name, self._vote_direction, self._confidence)

@pytest.fixture
def basic_context():
    return MarketContext(
        symbol=Symbol(name="BTC/USD", asset_class="CRYPTO"),
        features={},
        portfolio=Portfolio(),
        latest_prices={},
        memory_score=0.0
    )

def test_orchestrator_basic(basic_context):
    agents = [
        MockAgent("A1", "BUY", 0.9),
        MockAgent("A2", "BUY", 0.8),
        MockAgent("A3", "WAIT", 0.0)
    ]
    council = MultiAgentCouncil(agents=agents)
    verdict = council.evaluate(basic_context)
    
    assert verdict.final_vote == "BUY"
    assert verdict.position_size_multiplier == 1.0

def test_orchestrator_with_rl_policy(basic_context):
    agents = [
        MockAgent("A1", "BUY", 0.9), # Score: 0.9 * 0.8 = 0.72
        MockAgent("A2", "SELL", 0.8) # Score: 0.8 * 0.2 = 0.16
    ]
    policy = PolicyDecision(
        confidence_threshold_adjustment=0.1, # Min confidence is 0.5 + 0.1 = 0.6
        risk_multiplier=0.5,
        agent_weights={"A1": 0.8, "A2": 0.2}
    )
    
    council = MultiAgentCouncil(agents=agents)
    verdict = council.evaluate(basic_context, policy)
    
    assert verdict.final_vote == "BUY" # Since A1 is heavily weighted
    assert verdict.position_size_multiplier == 0.5 # Due to risk_multiplier

def test_orchestrator_rl_veto(basic_context):
    agents = [
        MockAgent("A1", "BUY", 0.5)
    ]
    policy = PolicyDecision(
        confidence_threshold_adjustment=0.2, # Min confidence 0.7
        risk_multiplier=1.0,
        agent_weights={}
    )
    
    council = MultiAgentCouncil(agents=agents)
    verdict = council.evaluate(basic_context, policy)
    
    # Aborted because confidence (0.5) < threshold (0.7)
    assert verdict.final_vote == "WAIT"
    assert verdict.veto_reason is not None

def test_orchestrator_create_order(basic_context):
    agents = [MockAgent("A1", "BUY", 0.9)]
    council = MultiAgentCouncil(agents=agents)
    verdict = council.evaluate(basic_context)
    
    order = council.create_order(verdict, basic_context.symbol, base_volume=0.1)
    assert order is not None
    assert order.action.value == "buy"
    from decimal import Decimal
    assert order.volume == Decimal("0.1")

def test_orchestrator_integration_with_risk_manager(basic_context):
    agents = [MockAgent("A1", "BUY", 0.9)]
    council = MultiAgentCouncil(agents=agents)
    verdict = council.evaluate(basic_context)
    
    order = council.create_order(verdict, basic_context.symbol, base_volume=0.1)
    
    # PortfolioEngine handles Risk Manager validation
    portfolio_engine = PortfolioEngine()
    portfolio_engine._latest_prices[basic_context.symbol] = Decimal("50000.0")

    is_approved, event = portfolio_engine.process_order(order)

    # Assuming it's approved by default if no drawdown limit breached
    assert is_approved is True
    assert event == order
