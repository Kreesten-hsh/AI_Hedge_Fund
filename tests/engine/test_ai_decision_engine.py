import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

from aegis_trade.engine.ai_decision_engine import AiDecisionEngine
from aegis_trade.engine.events import SignalEvent, SignalIntent, MarketEvent, OrderAction
from aegis_trade.domain.decisions import CouncilDecision
from aegis_trade.domain import MarketBar, Symbol, AssetClass, TimeFrame
from aegis_trade.engine.portfolio import Portfolio

class TestAiDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.mock_orchestrator = Mock()
        self.engine = AiDecisionEngine(orchestrator=self.mock_orchestrator, risk_pct=Decimal("0.10"), window_size=2)
        
        self.symbol = Symbol("XAUUSD", AssetClass.COMMODITIES)
        self.portfolio = Portfolio(initial_capital=Decimal("100000"))
        
        # Provide history
        ts = datetime.now(timezone.utc)
        bar1 = MarketBar(self.symbol, TimeFrame.H1, ts, Decimal("2000"), Decimal("2010"), Decimal("1990"), Decimal("2005"), 100)
        bar2 = MarketBar(self.symbol, TimeFrame.H1, ts, Decimal("2005"), Decimal("2015"), Decimal("2000"), Decimal("2010"), 100)
        
        self.portfolio.on_market_event(MarketEvent(timestamp=bar1.timestamp, bar=bar1))
        self.portfolio.on_market_event(MarketEvent(timestamp=bar2.timestamp, bar=bar2))
        
        self.engine.on_market_event(MarketEvent(timestamp=bar1.timestamp, bar=bar1))
        self.engine.on_market_event(MarketEvent(timestamp=bar2.timestamp, bar=bar2))

    def test_ai_reduces_position_size(self):
        # AI returns 0.5 multiplier
        self.mock_orchestrator.generate_decision.return_value = CouncilDecision(
            decision_type="go_long",
            confidence=0.8,
            multiplier=0.5,
            reasoning="Testing",
            supporting_reports=[]
        )
        
        event = SignalEvent(timestamp=datetime.now(timezone.utc), symbol=self.symbol, intent=SignalIntent.ENTER_LONG, strategy_id="test_strat")
        orders = self.engine.on_signal_event(event, self.portfolio)
        
        self.assertEqual(len(orders), 1)
        order = orders[0]
        self.assertEqual(order.action, OrderAction.BUY)
        
        # Standard size = 10% of 100,000 / 2010 = 10000 / 2010 = 4.975 -> 4.98
        # AI size = 4.975 * 0.5 = 2.487 -> 2.49
        self.assertEqual(order.volume, Decimal("2.49"))
        self.assertEqual(order.strategy_id, "test_strat_AI")
        
    def test_ai_rejects_signal(self):
        # AI returns reject
        self.mock_orchestrator.generate_decision.return_value = CouncilDecision(
            decision_type="reject",
            confidence=0.9,
            multiplier=0.0,
            reasoning="Testing reject",
            supporting_reports=[]
        )
        
        event = SignalEvent(timestamp=datetime.now(timezone.utc), symbol=self.symbol, intent=SignalIntent.ENTER_LONG, strategy_id="test_strat")
        orders = self.engine.on_signal_event(event, self.portfolio)
        
        self.assertEqual(len(orders), 0)

if __name__ == '__main__':
    unittest.main()
