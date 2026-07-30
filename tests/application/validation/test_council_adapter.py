import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from aegis_trade.domain.features import FeatureSet
from aegis_trade.domain.core import Symbol, TimeFrame, AssetClass
from aegis_trade.domain.council import CouncilVerdict, AgentVote
from aegis_trade.application.validation.council_adapter import CouncilBacktestAdapter
from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.domain.rl import IPolicyStore

def test_council_adapter_translates_buy_verdict_to_signal():
    # Setup
    council_mock = MagicMock(spec=MultiAgentCouncil)
    policy_store_mock = MagicMock(spec=IPolicyStore)
    policy_store_mock.load_active_policy.return_value = None # No active policy fallback
    
    adapter = CouncilBacktestAdapter(council=council_mock, policy_store=policy_store_mock)
    
    # Mock verdict
    verdict = CouncilVerdict(
        final_vote="BUY",
        aggregated_confidence=0.8,
        position_size_multiplier=1.0,
        votes=[],
        veto_reason=None,
        disagreement_level=0.1
    )
    council_mock.evaluate.return_value = verdict
    
    # Execute
    features = FeatureSet(
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        timeframe=TimeFrame.M15,
        timestamp=datetime.now(timezone.utc),
        features={"close": 150.0, "trend_score": 0.9}
    )
    signals = adapter.generate_signals(features)
    
    # Assert
    assert len(signals) == 1
    assert signals[0].symbol == features.symbol
    assert signals[0].direction == 1
    assert signals[0].strength == 0.8
    
    # Verify council was called correctly
    council_mock.evaluate.assert_called_once()
    context_arg = council_mock.evaluate.call_args[0][0]
    assert context_arg.symbol == features.symbol
    assert context_arg.features["trend_score"] == 0.9
    assert context_arg.latest_prices[features.symbol] == Decimal("150.0")

def test_council_adapter_returns_empty_on_wait():
    # Setup
    council_mock = MagicMock(spec=MultiAgentCouncil)
    policy_store_mock = MagicMock(spec=IPolicyStore)
    policy_store_mock.load_active_policy.return_value = None
    
    adapter = CouncilBacktestAdapter(council=council_mock, policy_store=policy_store_mock)
    
    verdict = CouncilVerdict(
        final_vote="WAIT",
        aggregated_confidence=0.2,
        position_size_multiplier=0.0,
        votes=[],
        veto_reason="Low conviction",
        disagreement_level=0.5
    )
    council_mock.evaluate.return_value = verdict
    
    features = FeatureSet(
        symbol=Symbol("AAPL", AssetClass.EQUITIES),
        timeframe=TimeFrame.M15,
        timestamp=datetime.now(timezone.utc),
        features={"close": 150.0}
    )
    signals = adapter.generate_signals(features)
    
    assert len(signals) == 0
