"""
Tests for Policy Evaluator.
"""

from unittest.mock import MagicMock
from aegis_trade.application.reinforcement_learning.policy_evaluator import PolicyEvaluator
from aegis_trade.domain.rl import IPolicyStore


def test_policy_evaluator_promotes():
    mock_store = MagicMock(spec=IPolicyStore)
    evaluator = PolicyEvaluator(policy_store=mock_store)
    
    # The dummy logic inside PolicyEvaluator currently always promotes if we don't change it,
    # but let's test the interface.
    promoted, reason = evaluator.evaluate("candidate_1", "current_1", [])
    assert promoted is True
    assert "promoted" in reason.lower()
