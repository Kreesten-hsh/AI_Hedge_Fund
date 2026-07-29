import pytest
from decimal import Decimal
from datetime import datetime, timezone
from aegis_trade.domain.core import Symbol, TimeFrame, Side, AssetClass
from aegis_trade.domain.memory import Experience, MarketFeatures, MemoryCategory
from aegis_trade.domain.reasoning import ClusterData
from aegis_trade.application.reasoning.analyzer import ExperienceAnalyzer, SimilarityAnalyzer

def test_experience_analyzer_pnl():
    analyzer = ExperienceAnalyzer()
    
    features = MarketFeatures(
        price=1.0, open_price=1.0, high_price=1.0, low_price=1.0, close_price=1.0,
        spread=0.0001, volume=100.0, order_book_imbalance=0.1, time_of_day=14.5,
        session="london", time_since_economic_event_min=60.0, economic_calendar_flag=False,
        ema_distance=0.0, rsi=50.0, macd=0.0, momentum_roc=0.0, vwap_distance=0.0,
        atr=0.0, volatility_state=0.0, liquidity_density=0.0, portfolio_correlation=0.0
    )
    
    experiences = [
        Experience("1", datetime.utcnow().replace(tzinfo=timezone.utc), Symbol("EURUSD", AssetClass.FOREX), TimeFrame.M1, features, Side.LONG, Decimal("10.0"), Decimal("0.0"), 100, MemoryCategory.SUCCESS, (0.0,)),
        Experience("2", datetime.utcnow().replace(tzinfo=timezone.utc), Symbol("EURUSD", AssetClass.FOREX), TimeFrame.M1, features, Side.LONG, Decimal("20.0"), Decimal("0.0"), 100, MemoryCategory.SUCCESS, (0.0,)),
        Experience("3", datetime.utcnow().replace(tzinfo=timezone.utc), Symbol("EURUSD", AssetClass.FOREX), TimeFrame.M1, features, Side.LONG, Decimal("-15.0"), Decimal("0.0"), 100, MemoryCategory.FAILURE, (0.0,))
    ]
    
    stats = analyzer.analyze_pnl_distribution(experiences)
    assert stats["mean"] == 5.0
    assert stats["median"] == 10.0
    assert stats["max"] == 20.0
    assert stats["min"] == -15.0

def test_similarity_analyzer():
    analyzer = SimilarityAnalyzer()
    
    cluster = ClusterData(
        cluster_id=1,
        size=10,
        experience_ids=[],
        centroid_features={"f_0": 10.0, "f_1": 5.0},
        variance_features={"f_0": 1.0, "f_1": 0.25},  # std_dev: f_0=1.0, f_1=0.5
        is_success_cluster=True
    )
    
    # Exactly on centroid
    assert analyzer.is_within_bounds({"f_0": 10.0, "f_1": 5.0}, cluster, max_std_dev=2.0)
    
    # Distance calculation
    dist = analyzer.calculate_distance({"f_0": 10.0, "f_1": 2.0}, cluster)
    assert dist == 3.0
    
    # Out of bounds for f_0 (diff is 3.0, allowed is 2 * 1.0 = 2.0)
    assert not analyzer.is_within_bounds({"f_0": 13.0, "f_1": 5.0}, cluster, max_std_dev=2.0)
    
    # In bounds for f_0 (diff is 2.0)
    assert analyzer.is_within_bounds({"f_0": 12.0, "f_1": 5.0}, cluster, max_std_dev=2.0)
