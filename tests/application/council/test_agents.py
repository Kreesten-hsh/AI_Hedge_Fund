import pytest
from decimal import Decimal
from aegis_trade.domain.council import MarketContext
from aegis_trade.engine.portfolio import Portfolio, EnginePosition
from aegis_trade.domain import Symbol
from aegis_trade.application.council.agents.trend_agent import TrendAgent
from aegis_trade.application.council.agents.momentum_agent import MomentumAgent
from aegis_trade.application.council.agents.volatility_agent import VolatilityAgent
from aegis_trade.application.council.agents.liquidity_agent import LiquidityAgent
from aegis_trade.application.council.agents.pattern_agent import PatternAgent
from aegis_trade.application.council.agents.portfolio_agent import PortfolioAgent
from aegis_trade.application.council.agents.execution_agent import ExecutionAgent
from aegis_trade.application.council.agents.news_agent import NewsAgent

@pytest.fixture
def empty_portfolio():
    return Portfolio(initial_capital=100000.0)

@pytest.fixture
def basic_context(empty_portfolio):
    return MarketContext(
        symbol=Symbol(name="BTC/USD", asset_class="CRYPTO"),
        features={
            "ema_50": 50000.0,
            "rsi": 50.0,
            "bb_upper": 51000.0,
            "bb_lower": 49000.0,
            "spread": 1.0,
            "broker_latency_ms": 10.0
        },
        portfolio=empty_portfolio,
        latest_prices={Symbol(name="BTC/USD", asset_class="CRYPTO"): Decimal("50000.0")},
        memory_score=0.0
    )

def test_trend_agent(basic_context):
    agent = TrendAgent()
    assert agent.name == "TrendAgent"
    
    # Neutral
    vote = agent.vote(basic_context)
    assert vote.vote == "WAIT"
    
    # Bullish
    basic_context.latest_prices[basic_context.symbol] = Decimal("51000.0")
    vote = agent.vote(basic_context)
    assert vote.vote == "BUY"
    
    # Bearish
    basic_context.latest_prices[basic_context.symbol] = Decimal("49000.0")
    vote = agent.vote(basic_context)
    assert vote.vote == "SELL"

def test_momentum_agent(basic_context):
    agent = MomentumAgent()
    assert agent.name == "MomentumAgent"
    
    # Neutral
    vote = agent.vote(basic_context)
    assert vote.vote == "WAIT"
    
    # Oversold (Bullish)
    basic_context.features["rsi"] = 25.0
    vote = agent.vote(basic_context)
    assert vote.vote == "BUY"
    
    # Overbought (Bearish)
    basic_context.features["rsi"] = 75.0
    vote = agent.vote(basic_context)
    assert vote.vote == "SELL"

def test_volatility_agent(basic_context):
    agent = VolatilityAgent()
    assert agent.name == "VolatilityAgent"
    
    # Neutral
    vote = agent.vote(basic_context)
    assert vote.vote == "WAIT"
    
    # Touches Upper Band (Mean Reversion -> SELL)
    basic_context.latest_prices[basic_context.symbol] = Decimal("51000.0")
    vote = agent.vote(basic_context)
    assert vote.vote == "SELL"
    
    # Touches Lower Band (Mean Reversion -> BUY)
    basic_context.latest_prices[basic_context.symbol] = Decimal("49000.0")
    vote = agent.vote(basic_context)
    assert vote.vote == "BUY"

def test_liquidity_agent(basic_context):
    agent = LiquidityAgent()
    
    # Normal Spread -> Neutral WAIT
    vote = agent.vote(basic_context)
    assert vote.vote == "WAIT"
    assert vote.confidence == 0.0
    
    # High Spread -> Veto WAIT
    basic_context.features["spread"] = 10.0
    vote = agent.vote(basic_context)
    assert vote.vote == "WAIT"
    assert vote.confidence == 0.9

def test_pattern_agent(basic_context):
    agent = PatternAgent()
    
    # Neutral
    vote = agent.vote(basic_context)
    assert vote.vote == "WAIT"
    
    # Positive Score
    basic_context = MarketContext(
        symbol=basic_context.symbol,
        features=basic_context.features,
        portfolio=basic_context.portfolio,
        latest_prices=basic_context.latest_prices,
        memory_score=50.0
    )
    vote = agent.vote(basic_context)
    assert vote.vote == "BUY"
    assert vote.confidence == 0.5
    
    # Negative Score
    basic_context = MarketContext(
        symbol=basic_context.symbol,
        features=basic_context.features,
        portfolio=basic_context.portfolio,
        latest_prices=basic_context.latest_prices,
        memory_score=-80.0
    )
    vote = agent.vote(basic_context)
    assert vote.vote == "SELL"
    assert vote.confidence == 0.8

def test_portfolio_agent(empty_portfolio, basic_context):
    agent = PortfolioAgent()
    
    # No position
    vote = agent.vote(basic_context)
    assert vote.vote == "WAIT"
    
    # Long position (Suggests reducing exposure)
    empty_portfolio._positions[basic_context.symbol] = EnginePosition(
        symbol=basic_context.symbol, volume=Decimal("1.0"), average_price=Decimal("50000.0")
    )
    vote = agent.vote(basic_context)
    assert vote.vote == "SELL"
    
    # Short position (Suggests reducing exposure)
    empty_portfolio._positions[basic_context.symbol].volume = Decimal("-1.0")
    vote = agent.vote(basic_context)
    assert vote.vote == "BUY"

def test_execution_agent(basic_context):
    agent = ExecutionAgent()
    
    # Low latency
    vote = agent.vote(basic_context)
    assert vote.vote == "WAIT"
    assert vote.confidence == 0.0
    
    # High latency
    basic_context.features["broker_latency_ms"] = 300.0
    vote = agent.vote(basic_context)
    assert vote.vote == "WAIT"
    assert vote.confidence == 0.95

def test_news_agent(basic_context):
    agent = NewsAgent()
    vote = agent.vote(basic_context)
    assert vote.vote == "WAIT"
    assert vote.confidence == 0.0
