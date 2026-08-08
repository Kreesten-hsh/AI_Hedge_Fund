import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock

from aegis_trade.engine.ai_decision_engine import ATR_PERIOD, AiDecisionEngine
from aegis_trade.engine.events import SignalEvent, SignalIntent, MarketEvent, OrderAction
from aegis_trade.domain.council import CouncilVerdict, AgentVote
from aegis_trade.domain import MarketBar, Symbol, AssetClass, TimeFrame
from aegis_trade.engine.portfolio import Portfolio

class TestAiDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.mock_council = Mock()
        self.engine = AiDecisionEngine(council=self.mock_council, risk_pct=Decimal("0.10"), window_size=2)

        self.symbol = Symbol("XAUUSD", AssetClass.COMMODITIES)
        self.portfolio = Portfolio(initial_capital=Decimal("100000"))

        start = datetime.now(timezone.utc)
        bars = []
        for i in range(ATR_PERIOD + 1):
            close = Decimal("2005") + Decimal(i) * Decimal("5")
            bars.append(MarketBar(
                symbol=self.symbol,
                timeframe=TimeFrame.H1,
                timestamp=start + timedelta(hours=i),
                open=close - Decimal("5"),
                high=close + Decimal("5"),
                low=close - Decimal("10"),
                close=close,
                volume=Decimal("100"),
            ))

        self.latest_close = bars[-1].close

        for bar in bars:
            event = MarketEvent(timestamp=bar.timestamp, bar=bar)
            self.portfolio.on_market_event(event)
            self.engine.on_market_event(event)

    def test_ai_reduces_position_size(self):
        # AI returns BUY verdict with 0.5 multiplier
        self.mock_council.evaluate.return_value = CouncilVerdict(
            final_vote="BUY",
            aggregated_confidence=0.8,
            position_size_multiplier=0.5,
            votes=[],
            veto_reason=None,
            disagreement_level=0.0
        )

        event = SignalEvent(timestamp=datetime.now(timezone.utc), symbol=self.symbol, intent=SignalIntent.ENTER_LONG, strategy_id="test_strat")
        orders = self.engine.on_signal_event(event, self.portfolio)

        self.assertEqual(len(orders), 1)
        order = orders[0]
        self.assertEqual(order.action, OrderAction.BUY)

        expected_volume = round(
            (Decimal("100000") * Decimal("0.10") / self.latest_close) * Decimal("0.5"), 2
        )
        self.assertEqual(order.volume, expected_volume)
        self.assertEqual(order.strategy_id, "test_strat_AI")

    def test_ai_receives_a_measured_atr_not_a_fabricated_one(self):
        """Le contexte envoyé au Council porte un ATR calculé par l'autorité."""
        self.mock_council.evaluate.return_value = CouncilVerdict(
            final_vote="BUY", aggregated_confidence=0.8, position_size_multiplier=1.0,
            votes=[], veto_reason=None, disagreement_level=0.0
        )

        event = SignalEvent(timestamp=datetime.now(timezone.utc), symbol=self.symbol, intent=SignalIntent.ENTER_LONG, strategy_id="test_strat")
        self.engine.on_signal_event(event, self.portfolio)

        context = self.mock_council.evaluate.call_args.args[0]
        atr_stats = self.engine._atr_stats()
        assert atr_stats is not None
        expected_atr, expected_avg = atr_stats
        self.assertEqual(context.features["atr"], expected_atr)
        self.assertEqual(context.features["avg_atr"], expected_avg)
        self.assertGreater(context.features["atr"], 0.0)

    def test_no_order_without_a_computable_atr(self):
        """En deçà de l'amorce de Wilder, le moteur s'abstient au lieu d'inventer."""
        engine = AiDecisionEngine(council=self.mock_council, risk_pct=Decimal("0.10"), window_size=2)
        start = datetime.now(timezone.utc)
        for i in range(ATR_PERIOD):
            close = Decimal("2005") + Decimal(i) * Decimal("5")
            bar = MarketBar(
                symbol=self.symbol, timeframe=TimeFrame.H1,
                timestamp=start + timedelta(hours=i),
                open=close - Decimal("5"), high=close + Decimal("5"),
                low=close - Decimal("10"), close=close, volume=Decimal("100"),
            )
            engine.on_market_event(MarketEvent(timestamp=bar.timestamp, bar=bar))

        event = SignalEvent(timestamp=datetime.now(timezone.utc), symbol=self.symbol, intent=SignalIntent.ENTER_LONG, strategy_id="test_strat")
        orders = engine.on_signal_event(event, self.portfolio)

        self.assertEqual(orders, [])
        self.mock_council.evaluate.assert_not_called()

    def test_ai_rejects_signal(self):
        # AI returns WAIT verdict
        self.mock_council.evaluate.return_value = CouncilVerdict(
            final_vote="WAIT",
            aggregated_confidence=0.9,
            position_size_multiplier=0.0,
            votes=[],
            veto_reason="Testing reject",
            disagreement_level=0.0
        )
        
        event = SignalEvent(timestamp=datetime.now(timezone.utc), symbol=self.symbol, intent=SignalIntent.ENTER_LONG, strategy_id="test_strat")
        orders = self.engine.on_signal_event(event, self.portfolio)
        
        self.assertEqual(len(orders), 0)

if __name__ == '__main__':
    unittest.main()
