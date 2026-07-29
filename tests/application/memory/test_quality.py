import pytest
from datetime import datetime, timezone
from decimal import Decimal
import dataclasses

from aegis_trade.domain.core import Symbol, TimeFrame, Side, AssetClass
from aegis_trade.domain.memory import Experience, MarketFeatures, MemoryCategory
from aegis_trade.application.memory.quality import ExperienceQualityAnalyzer, QualityViolation

@pytest.fixture
def base_features():
    return MarketFeatures(
        price=1.0500,
        open_price=1.0490,
        high_price=1.0510,
        low_price=1.0480,
        close_price=1.0500,
        spread=0.0001,
        volume=100.0,
        order_book_imbalance=0.1,
        time_of_day=14.5,
        session="london",
        time_since_economic_event_min=60.0,
        economic_calendar_flag=False,
        ema_distance=0.001,
        rsi=50.0,
        macd=0.0001,
        momentum_roc=0.01,
        vwap_distance=0.001,
        atr=0.0010,
        volatility_state=0.5,
        liquidity_density=10.0,
        portfolio_correlation=0.1
    )

@pytest.fixture
def base_experience(base_features):
    return Experience(
        id="exp-1",
        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        symbol=Symbol("EURUSD", AssetClass.FOREX),
        timeframe=TimeFrame.M1,
        features=base_features,
        decision_side=Side.LONG,
        pnl=Decimal("10.0"),
        max_drawdown=Decimal("1.0"),
        duration_seconds=300,
        category=MemoryCategory.SUCCESS,
        embedding=(0.1, 0.2, 0.3)
    )

def test_valid_experience_passes(base_experience):
    analyzer = ExperienceQualityAnalyzer()
    analyzer.analyze(base_experience) # Should not raise

def test_too_long_duration_raises(base_experience):
    base_experience = dataclasses.replace(base_experience, duration_seconds=3600 * 24 * 40) # 40 days
    analyzer = ExperienceQualityAnalyzer()
    with pytest.raises(QualityViolation, match="Duration too long"):
        analyzer.analyze(base_experience)

def test_absurd_spread_raises(base_experience, base_features):
    # Set spread to 20% of price
    bad_features = dataclasses.replace(base_features, spread=0.21)
    base_experience = dataclasses.replace(base_experience, features=bad_features)
    
    analyzer = ExperienceQualityAnalyzer()
    with pytest.raises(QualityViolation, match="Spread is absurdly high"):
        analyzer.analyze(base_experience)

def test_invalid_ohlc_raises(base_experience, base_features):
    bad_features = dataclasses.replace(base_features, low_price=1.06, high_price=1.05) # low > high
    base_experience = dataclasses.replace(base_experience, features=bad_features)
    
    analyzer = ExperienceQualityAnalyzer()
    with pytest.raises(QualityViolation, match="is greater than High price"):
        analyzer.analyze(base_experience)

def test_invalid_rsi_raises(base_experience, base_features):
    bad_features = dataclasses.replace(base_features, rsi=101.0)
    base_experience = dataclasses.replace(base_experience, features=bad_features)
    
    analyzer = ExperienceQualityAnalyzer()
    with pytest.raises(QualityViolation, match="RSI out of bounds"):
        analyzer.analyze(base_experience)
