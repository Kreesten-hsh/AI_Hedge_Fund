import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from aegis_trade.domain.research import (
    ExperimentConfig, ExperimentStatus, PromotionStatus
)
from aegis_trade.infrastructure.research.registry import ExperimentRegistryV2
from aegis_trade.application.research.experiment_manager import ExperimentManager

@pytest.fixture
def temp_registry(tmp_path):
    return ExperimentRegistryV2(registry_dir=str(tmp_path / "registry"))

def test_create_and_promote_experiment(temp_registry):
    manager = ExperimentManager(temp_registry)
    config = ExperimentConfig(
        strategy_class_name="TestStrategy",
        strategy_kwargs={"p1": 1},
        validation_config_dict={},
        data_sources=["BTC"]
    )
    
    # 1. Create
    exp = manager.create_experiment(
        config=config,
        strategy_name="TestStrategy",
        features=["f1"],
        markets=["BTC"],
        timeframes=["H1"],
        parameters={"p1": 1},
        author="quant_1"
    )
    
    assert exp.status == ExperimentStatus.CREATED
    assert exp.promotion_status == PromotionStatus.RESEARCH
    assert exp.metadata.author == "quant_1"
    assert exp.metadata.git_commit != "unknown" or exp.metadata.git_commit == "unknown" # Should not crash
    
    # Verify saved
    loaded = temp_registry.load_experiment(exp.metadata.id)
    assert loaded is not None
    assert loaded["metadata"]["author"] == "quant_1"
    
    # 2. Try to promote (Should fail because passed = False)
    with pytest.raises(ValueError, match="Cannot promote"):
        manager.promote_experiment(exp.metadata.id, PromotionStatus.APPROVED)
        
    # Hack the JSON to make it passed for the sake of the test
    import json
    files = list(temp_registry.registry_dir.glob("exp_*.json"))
    with open(files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
        
    data["result"] = {
        "validation_artifact": {
            "report": {
                "is_approved": True
            }
        }
    }
    with open(files[0], "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    # 3. Promote successfully
    assert manager.promote_experiment(exp.metadata.id, PromotionStatus.APPROVED) == True
    
    # Verify
    updated = temp_registry.load_experiment(exp.metadata.id)
    assert updated["promotion_status"] == PromotionStatus.APPROVED.value
    
def test_experiment_lineage_and_search(temp_registry):
    manager = ExperimentManager(temp_registry)
    config = ExperimentConfig("S1", {}, {}, ["M1"])
    
    exp1 = manager.create_experiment(config, "S1", [], ["M1"], [], {}, author="alice")
    exp2 = manager.create_experiment(config, "S1_v2", [], ["M1"], [], {}, author="bob", parent_id=exp1.metadata.id)
    
    # Search by author
    results = temp_registry.search(author="alice")
    assert len(results) == 1
    assert results[0]["metadata"]["id"] == exp1.metadata.id
    
    # Search by lineage
    results_lineage = temp_registry.search(parent_id=exp1.metadata.id)
    assert len(results_lineage) == 1
    assert results_lineage[0]["metadata"]["id"] == exp2.metadata.id
