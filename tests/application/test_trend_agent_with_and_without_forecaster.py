import pytest
from aegis_trade.application.council.agents.trend_agent import TrendAgent
from aegis_trade.domain.council import MarketContext, AgentVote
from aegis_trade.domain.forecasting import IForecaster, KronosForecast

class MockBullishForecaster(IForecaster):
    def get_latest_forecast(self, symbol: str):
        return KronosForecast(
            symbol=symbol,
            horizon=10,
            predicted_values=[150.0] * 10, # Very bullish
            confidence_interval=(140.0, 160.0),
            model_version="test"
        )

class MockBearishForecaster(IForecaster):
    def get_latest_forecast(self, symbol: str):
        return KronosForecast(
            symbol=symbol,
            horizon=10,
            predicted_values=[50.0] * 10, # Very bearish
            confidence_interval=(40.0, 60.0),
            model_version="test"
        )

def test_trend_agent_fallback_no_regression():
    # 1. No forecaster
    agent_no_forecaster = TrendAgent(forecaster=None)
    
    # 2. Forecaster available
    agent_with_forecaster = TrendAgent(forecaster=MockBullishForecaster())
    
    context = MarketContext(
        symbol="TEST",
        latest_prices={"TEST": 100.0},
        features={"ema_50": 95.0}, # price > ema -> base vote is BUY 0.7
        memory_score=0.0,
        portfolio={}
    )
    
    vote1 = agent_no_forecaster.vote(context)
    assert vote1.vote == "BUY"
    assert vote1.confidence == 0.7
    
    vote2 = agent_with_forecaster.vote(context)
    assert vote2.vote == "BUY"
    assert vote2.confidence > 0.7 # Boosted by bullish forecast

def test_trend_agent_disagreement_lowers_confidence():
    agent = TrendAgent(forecaster=MockBearishForecaster())
    
    context = MarketContext(
        symbol="TEST",
        latest_prices={"TEST": 100.0},
        features={"ema_50": 95.0}, # base is BUY 0.7
        memory_score=0.0,
        portfolio={}
    )
    
    vote = agent.vote(context)
    # Bearish forecast contradicts BUY base vote
    assert vote.vote == "BUY"
    assert vote.confidence < 0.7 # Confidence should be reduced
