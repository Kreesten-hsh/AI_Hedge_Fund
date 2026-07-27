import pytest
import os
import json
from datetime import datetime
from unittest.mock import Mock, patch

from aegis_trade.domain.validation import ValidationCampaignType
from aegis_trade.application.validation.config import ValidationConfig
from aegis_trade.engine.scoring_engine import ScoringEngine
from aegis_trade.infrastructure.validation.registry import ValidationRegistry
from aegis_trade.application.validation.validation_runner import ValidationRunner

@pytest.fixture
def temp_registry(tmp_path):
    # Use tmp_path fixture for clean test directory
    registry_path = tmp_path / "registry"
    return ValidationRegistry(registry_dir=str(registry_path))

def test_validation_runner_full_suite(temp_registry):
    scoring_engine = ScoringEngine()
    runner = ValidationRunner(registry=temp_registry, scoring_engine=scoring_engine)
    
    config = ValidationConfig(
        active_campaigns=[ValidationCampaignType.HOLD_OUT, ValidationCampaignType.MONTE_CARLO],
        seed=123
    )
    
    mock_strategy = Mock()
    mock_strategy.__class__.__name__ = "MockStrategy"
    
    mock_data = Mock()
    mock_broker_factory = Mock
    
    artifact = runner.run_validation(
        strategy=mock_strategy,
        data_feed=mock_data,
        broker_factory=mock_broker_factory,
        config=config
    )
    
    # Verify Context reproducibility
    assert artifact.context.seed == 123
    assert artifact.context.strategy_version == "MockStrategy"
    
    # Verify Campaigns ran
    campaign_types_run = [c.campaign_type for c in artifact.report.campaigns]
    assert ValidationCampaignType.HOLD_OUT in campaign_types_run
    assert ValidationCampaignType.MONTE_CARLO in campaign_types_run
    
    # Verify Score
    assert artifact.report.strategy_score > 0
    assert artifact.report.is_approved is False # 10 (hold out pass) + 10 (mc pass) + 20 (ruin_prob) = 40. Not 75
    
    # Verify Registry persisted
    files = temp_registry.list_artifacts()
    assert len(files) == 1
    
    # Load and verify JSON persistence works
    with open(files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert data["context"]["seed"] == 123
        assert data["report"]["strategy_score"] == artifact.report.strategy_score
