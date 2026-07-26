import unittest
from unittest.mock import Mock
import json
import os

from aegis_trade.agents.synthesizer import CouncilSynthesizer
from aegis_trade.domain.reports import ResearchReport

class TestCouncilSynthesizer(unittest.TestCase):
    def setUp(self):
        self.mock_provider = Mock()
        self.synthesizer = CouncilSynthesizer(provider=self.mock_provider)

    def test_conflict_resolution(self):
        # Fake reports
        report_macro = ResearchReport(
            capability="macro_analysis",
            data={"macro_bias": "bullish", "confidence": 0.9}
        )
        report_regime = ResearchReport(
            capability="regime_analysis",
            data={"regime": "bearish", "confidence": 0.8}
        )
        report_risk = ResearchReport(
            capability="risk_analysis",
            data={"volatility_assessment": "extreme", "suggested_multiplier": 0.0}
        )
        
        # Mock LLM response resolving conflict
        fake_response = {
            "decision_type": "reject",
            "confidence": 0.95,
            "multiplier": 0.0,
            "reasoning": "Conflicting macro and regime signals, combined with extreme risk, warrants rejection."
        }
        self.mock_provider.generate.return_value = json.dumps(fake_response)
        
        decision = self.synthesizer.synthesize(reports=[report_macro, report_regime, report_risk], intent="LONG")
        
        self.assertEqual(decision.decision_type, "reject")
        self.assertEqual(decision.multiplier, 0.0)
        self.assertEqual(len(decision.supporting_reports), 3)

if __name__ == '__main__':
    unittest.main()
