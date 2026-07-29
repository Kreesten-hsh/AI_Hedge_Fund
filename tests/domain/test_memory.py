from datetime import datetime, timezone
from decimal import Decimal
import pytest

from aegis_trade.domain.core import Symbol, AssetClass, TimeFrame, Side
from aegis_trade.domain.memory import (
    Experience, MarketFeatures, MarketSession, MemoryCategory, SearchResult
)

def test_market_features_creation():
    features = MarketFeatures(
        price=1.1000,
        open_price=1.0950,
        high_price=1.1050,
        low_price=1.0900,
        close_price=1.1000,
        spread=0.0002,
        volume=1000.0,
        order_book_imbalance=0.1,
        time_of_day=14.5,
        session=MarketSession.NEW_YORK,
        time_since_economic_event_min=30.0,
        economic_calendar_flag=False,
        ema_distance=0.005,
        rsi=65.0,
        macd=0.001,
        momentum_roc=0.02,
        vwap_distance=0.002,
        atr=0.0015,
        volatility_state=1.2,
        liquidity_density=500.0,
        portfolio_correlation=0.5
    )
    assert features.price == 1.1000
    assert features.session == MarketSession.NEW_YORK

def test_experience_validation():
    features = MarketFeatures(
        price=1.1, open_price=1.1, high_price=1.1, low_price=1.1, close_price=1.1,
        spread=0.0, volume=0.0, order_book_imbalance=0.0, time_of_day=0.0, session=MarketSession.OTHER,
        time_since_economic_event_min=0.0, economic_calendar_flag=False, ema_distance=0.0, rsi=50.0,
        macd=0.0, momentum_roc=0.0, vwap_distance=0.0, atr=0.0, volatility_state=0.0, liquidity_density=0.0,
        portfolio_correlation=0.0
    )
    
    symbol = Symbol("EURUSD", AssetClass.FOREX)
    
    # Valid Experience
    exp = Experience(
        id="test-id",
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=symbol,
        timeframe=TimeFrame.M1,
        features=features,
        decision_side=Side.LONG,
        pnl=Decimal("10.0"),
        max_drawdown=Decimal("1.0"),
        duration_seconds=60,
        category=MemoryCategory.SUCCESS,
        embedding=(0.1, 0.2, 0.3)
    )
    assert exp.id == "test-id"

    # Invalid timestamp
    with pytest.raises(ValueError):
        Experience(
            id="test-id",
            timestamp=datetime(2023, 1, 1), # No timezone
            symbol=symbol,
            timeframe=TimeFrame.M1,
            features=features,
            decision_side=Side.LONG,
            pnl=Decimal("10.0"),
            max_drawdown=Decimal("1.0"),
            duration_seconds=60,
            category=MemoryCategory.SUCCESS,
            embedding=(0.1, 0.2, 0.3)
        )

    # Empty embedding
    with pytest.raises(ValueError):
        Experience(
            id="test-id",
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            symbol=symbol,
            timeframe=TimeFrame.M1,
            features=features,
            decision_side=Side.LONG,
            pnl=Decimal("10.0"),
            max_drawdown=Decimal("1.0"),
            duration_seconds=60,
            category=MemoryCategory.SUCCESS,
            embedding=()
        )

def test_search_result_validation():
    # ... mock experience ...
    features = MarketFeatures(
        1,1,1,1,1,0,0,0,0,MarketSession.OTHER,0,False,0,50,0,0,0,0,0,0,0
    )
    exp = Experience(
        id="1", timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=Symbol("X", AssetClass.FOREX), timeframe=TimeFrame.M1,
        features=features, decision_side=Side.LONG, pnl=Decimal("0"),
        max_drawdown=Decimal("0"), duration_seconds=1,
        category=MemoryCategory.SUCCESS, embedding=(1.0,)
    )
    
    sr = SearchResult(exp, 0.1, 95.0)
    assert sr.similarity_score == 95.0
    
    with pytest.raises(ValueError):
        SearchResult(exp, 0.1, 150.0)
