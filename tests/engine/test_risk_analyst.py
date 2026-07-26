import unittest
from unittest.mock import Mock
import json
import os

from aegis_trade.agents.risk_analyst import RiskAnalyst
from aegis_trade.agents.runner import AgentRunner
from aegis_trade.domain.reports import ResearchReport

class TestRiskAnalyst(unittest.TestCase):
    def setUp(self):
        self.mock_provider = Mock()
        self.runner = AgentRunner(provider=self.mock_provider)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.prompt_path = os.path.join(base_dir, "prompts", "risk_v1.md")

        self.agent = RiskAnalyst(prompt_path=self.prompt_path)

    def test_risk_analyst_extreme_volatility(self):
        # Mock LLM response
        fake_response = {
            "volatility_assessment": "extreme",
            "suggested_multiplier": 0.25,
            "reasoning": "ATR is 3x historical average."
        }
        self.mock_provider.generate.return_value = json.dumps(fake_response)

        context = {
            "atr": 45.0,
            "avg_atr": 15.0,
            "volatility_regime": "Spike"
        }

        result = self.runner.execute(self.agent, context)
        
        self.assertTrue(result.metadata.success)
        self.assertEqual(result.report.capability, "risk_analysis")
        self.assertEqual(result.report.data["volatility_assessment"], "extreme")
        self.assertEqual(result.report.data["suggested_multiplier"], 0.25)

if __name__ == '__main__':
    unittest.main()
