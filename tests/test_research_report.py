import pytest
import json
import os
import tempfile
from datetime import datetime, timezone
from dataclasses import asdict

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame
from aegis_trade.domain.research import ResearchMetadata, FeatureScore, AlphaResearchResult
from aegis_trade.infrastructure.research.research_report import ResearchReport

@pytest.fixture
def dummy_result():
    metadata = ResearchMetadata(
        symbol=Symbol("BTCUSD", AssetClass.CRYPTO),
        timeframe=TimeFrame.D1,
        start_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
        forward_returns_lag=1,
        computation_timestamp=datetime(2023, 1, 3, tzinfo=timezone.utc)
    )
    
    score = FeatureScore(
        feature_name="test_feat",
        mean=0.1,
        variance=0.2,
        std_dev=0.3,
        skewness=0.4,
        kurtosis=0.5,
        missing_rate=0.0,
        ic_mean=0.6,
        ic_std=0.7,
        ic_information_ratio=0.8,
        stability=0.9,
        final_score=0.72
    )
    
    return AlphaResearchResult(
        metadata=metadata,
        feature_scores={"test_feat": score},
        correlation_matrix={"test_feat": {"test_feat": 1.0}},
        top_features=["test_feat"],
        bottom_features=[]
    )

def test_research_report_generate_json(dummy_result):
    json_str = ResearchReport.generate_json(dummy_result)
    data = json.loads(json_str)
    
    assert "metadata" in data
    assert data["metadata"]["symbol"]["name"] == "BTCUSD"
    assert data["metadata"]["timeframe"] == "D1"
    assert data["metadata"]["forward_returns_lag"] == 1
    
    assert "feature_scores" in data
    assert "test_feat" in data["feature_scores"]
    assert data["feature_scores"]["test_feat"]["final_score"] == 0.72

def test_research_report_save_json(dummy_result):
    with tempfile.TemporaryDirectory() as temp_dir:
        filepath = os.path.join(temp_dir, "report.json")
        ResearchReport.generate_json(dummy_result, filepath=filepath)
        
        assert os.path.exists(filepath)
        with open(filepath, "r") as f:
            data = json.load(f)
            
        assert data["metadata"]["symbol"]["name"] == "BTCUSD"
