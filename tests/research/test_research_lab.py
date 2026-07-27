import pytest
import os
import json
from unittest.mock import Mock

from aegis_trade.domain.validation import ValidationArtifact, ValidationReport, ValidationCampaignResult, ValidationCampaignType, ValidationContext
from aegis_trade.application.research.search_space import GridSearchSpace
from aegis_trade.application.research.experiment_runner import ExperimentRunner
from aegis_trade.infrastructure.research.registry import ExperimentRegistryV2
from aegis_trade.application.research.comparison import ExperimentComparator
from aegis_trade.application.research.leaderboard import Leaderboard, ReportGenerator
from datetime import datetime, timezone

@pytest.fixture
def temp_registry(tmp_path):
    registry_path = tmp_path / "research_registry"
    return ExperimentRegistryV2(registry_dir=str(registry_path))

def test_search_space():
    space = GridSearchSpace("MyStrategy", {"some": "config"}, ["BTC"])
    space.add_parameter("ema_fast", [10, 20])
    space.add_parameter("ema_slow", [50, 200])
    
    configs = list(space.generate_configs())
    assert len(configs) == 4
    assert configs[0].strategy_kwargs == {"ema_fast": 10, "ema_slow": 50}
    assert configs[-1].strategy_kwargs == {"ema_fast": 20, "ema_slow": 200}

def test_research_lab_pipeline(temp_registry):
    # Mocking external components
    mock_validation_runner = Mock()
    mock_context = ValidationContext(seed=1, strategy_version="v1", config_version="v1", data_hash="h", timestamp=datetime.now(timezone.utc), git_version="1")
    mock_artifact = ValidationArtifact(
        context=mock_context,
        report=ValidationReport(
            is_approved=True,
            strategy_score=85.0,
            campaigns=[
                ValidationCampaignResult(
                    campaign_type=ValidationCampaignType.HOLD_OUT,
                    passed=True,
                    metrics={"sharpe_ratio": 1.5, "win_rate": 0.6},
                    details={}
                )
            ]
        ),
        parameters={}
    )
    mock_validation_runner.run_validation.return_value = mock_artifact
    
    def mock_strategy_factory(name, kwargs):
        return Mock()
        
    def mock_data_feed_factory(source):
        return Mock()
        
    runner = ExperimentRunner(
        registry=temp_registry,
        validation_runner=mock_validation_runner,
        strategy_factory=mock_strategy_factory,
        data_feed_factory=mock_data_feed_factory,
        broker_factory=Mock
    )
    
    # 1. Generate Configs
    space = GridSearchSpace("MyStrategy", {"seed": 123}, ["BTC"])
    space.add_parameter("param1", [1, 2])
    configs = list(space.generate_configs())
    
    # 2. Run Experiments
    for c in configs:
        runner.run_experiment(c)
        
    # Verify persistence
    files = temp_registry.list_experiments()
    assert len(files) == 2
    
    # 3. Compare and Leaderboard
    comparator = ExperimentComparator(temp_registry)
    leaderboard = Leaderboard(comparator)
    
    ranking = leaderboard.generate_ranking(sort_key="score")
    assert len(ranking) == 2
    assert ranking[0]["score"] == 85.0
    assert ranking[0]["sharpe"] == 1.5
    
    # 4. Report
    report_gen = ReportGenerator(leaderboard, report_dir=str(temp_registry.registry_dir))
    md_file = report_gen.generate_markdown()
    assert os.path.exists(md_file)
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "Aegis Quant OS - Research Leaderboard" in content
        assert "MyStrategy" in content
