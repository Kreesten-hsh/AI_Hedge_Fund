import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, create_autospec
from decimal import Decimal
from typing import AsyncGenerator

from aegis_trade.application.paper_trading.orchestrator import PaperTradingOrchestrator
from aegis_trade.application.paper_trading.interfaces import IPaperBroker, IMarketFeed
from aegis_trade.domain.core import AssetClass, MarketBar, Symbol, TimeFrame
from aegis_trade.engine.global_risk import GlobalRiskManager
from aegis_trade.engine.portfolio import PortfolioEngine
from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.domain.rl import IPolicyStore
from aegis_trade.domain.council import CouncilVerdict

AAPL = Symbol(name="AAPL", asset_class=AssetClass.EQUITIES)

# Mock feed for testing
class MockFeed(IMarketFeed):
    def __init__(self, bars):
        self.bars = bars
        
    async def subscribe(self) -> AsyncGenerator:
        for bar in self.bars:
            yield bar

@pytest.mark.anyio
async def test_orchestrator_council_integration():
    """
    Verifies that _process_feed correctly builds MarketContext, calls MultiAgentCouncil,
    validates the resulting order with RiskManager, and submits it to the broker.
    """
    # Doubles à signature vérifiée : `MagicMock(spec=...)` accepte n'importe
    # quels arguments, donc il laissait passer un appel à 3 arguments là où la
    # production en passe 4. `create_autospec` échoue au moment de l'appel.
    broker = create_autospec(IPaperBroker, instance=True)
    broker.submit_order = AsyncMock()

    # Une vraie `MarketBar` et non un MagicMock : le flux produit des bars
    # horodatées en UTC, et l'orchestrateur les pousse désormais dans le
    # portefeuille (Lot 2D). Un double sans timestamp réel laisserait passer
    # une régression que la production rejetterait.
    bar_mock = MarketBar(
        symbol=AAPL,
        timeframe=TimeFrame.M1,
        timestamp=datetime.now(timezone.utc),
        open=Decimal("150.0"),
        high=Decimal("150.0"),
        low=Decimal("150.0"),
        close=Decimal("150.0"),
        volume=Decimal("1000"),
    )
    feed = MockFeed([bar_mock])

    risk_manager = create_autospec(GlobalRiskManager, instance=True)
    risk_manager.validate_order.return_value = (True, "OK")

    portfolio_engine = create_autospec(PortfolioEngine, instance=True)

    council = create_autospec(MultiAgentCouncil, instance=True)
    
    # Setup council mock to return a valid BUY verdict
    mock_verdict = CouncilVerdict(
        final_vote="BUY",
        aggregated_confidence=0.8,
        position_size_multiplier=1.2,
        votes=[],
        veto_reason=None,
        disagreement_level=0.1
    )
    council.evaluate.return_value = mock_verdict
    
    # Mock create_order output
    from aegis_trade.engine.events import OrderEvent, OrderAction
    order_event_mock = OrderEvent(
        symbol=AAPL,
        action=OrderAction.BUY,
        volume=Decimal("1.2"),
        order_type="MARKET",
        timestamp=datetime.now(timezone.utc)
    )
    council.create_order.return_value = order_event_mock
    
    policy_store = create_autospec(IPolicyStore, instance=True)
    policy_store.load_active_policy.return_value = None # Fallback to equal weights
    
    event_publisher = AsyncMock()
    
    # Initialize Orchestrator
    orchestrator = PaperTradingOrchestrator(
        broker=broker,
        feed=feed,
        risk_manager=risk_manager,
        portfolio_engine=portfolio_engine,
        event_publisher=event_publisher,
        council=council,
        policy_store=policy_store
    )
    
    # Run _process_feed
    orchestrator.is_running = True
    await orchestrator._process_feed()
    
    # Assertions
    # 1. Active policy should have been checked
    policy_store.load_active_policy.assert_called_once()
    
    # 2. Council evaluate should be called
    council.evaluate.assert_called_once()
    
    # 3. Council create_order should be called with base volume 1.0 and the context
    council.create_order.assert_called_once()
    create_args = council.create_order.call_args[0]
    assert create_args[0] == mock_verdict
    assert create_args[1] == AAPL
    assert create_args[2] == 1.0
    assert create_args[3].symbol == AAPL
    
    # 4. Risk Manager validate_order should be called (not evaluate_order)
    risk_manager.validate_order.assert_called_once()
    assert risk_manager.validate_order.call_args[0][0] == order_event_mock
    
    # 5. Broker should have received a PaperOrder
    broker.submit_order.assert_called_once()
    paper_order = broker.submit_order.call_args[0][0]
    
    from aegis_trade.domain.paper.models import ActionType, OrderType
    assert paper_order.symbol == AAPL
    assert paper_order.action == ActionType.BUY
    assert paper_order.order_type == OrderType.MARKET
    assert paper_order.volume == Decimal("1.2")
