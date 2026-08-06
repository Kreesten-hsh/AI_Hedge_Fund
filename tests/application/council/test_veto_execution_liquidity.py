"""Test unitaire vérifiant le veto effectif de LiquidityAgent et ExecutionAgent."""

import pytest
from decimal import Decimal

from aegis_trade.domain.core import Symbol, AssetClass
from aegis_trade.domain.council import MarketContext, AgentVote
from aegis_trade.engine.portfolio import Portfolio
from aegis_trade.application.council.orchestrator import MultiAgentCouncil
from aegis_trade.application.council.agents.trend_agent import TrendAgent
from aegis_trade.application.council.agents.momentum_agent import MomentumAgent
from aegis_trade.application.council.agents.execution_agent import ExecutionAgent
from aegis_trade.application.council.agents.liquidity_agent import LiquidityAgent


def test_execution_agent_veto_overrides_buy_votes():
    """ExecutionAgent votant WAIT avec confiance >= 0.8 (ex: latence > 200ms) doit annuler les votes BUY."""
    symbol = Symbol(name="frxXAUUSD", asset_class=AssetClass.COMMODITIES)
    portfolio = Portfolio(initial_capital=Decimal("10000.0"))

    # Features: EMA et RSI indiquent un fort BUY, mais broker_latency_ms est à 250ms (supérieur à 200ms)
    features = {
        "ema_50": 2000.0,
        "rsi": 25.0,  # MomentumAgent vote BUY (conf 0.8)
        "broker_latency_ms": 250.0,  # ExecutionAgent vote WAIT (conf 0.95)
    }
    latest_prices = {symbol: Decimal("2050.0")}  # TrendAgent vote BUY (price > ema_50 * 1.001)

    context = MarketContext(
        symbol=symbol,
        features=features,
        portfolio=portfolio,
        latest_prices=latest_prices,
    )

    agents = [TrendAgent(), MomentumAgent(), ExecutionAgent()]
    council = MultiAgentCouncil(agents=agents)

    verdict = council.evaluate(context)

    # Avant le fix, verdict.final_vote était "BUY" car ExecutionAgent était ignoré dans l'agrégation
    assert verdict.final_vote == "WAIT"
    assert verdict.position_size_multiplier == 0.0
    assert verdict.veto_reason is not None
    assert "ExecutionAgent" in verdict.veto_reason


def test_liquidity_agent_veto_overrides_buy_votes():
    """LiquidityAgent votant WAIT avec confiance >= 0.8 (ex: spread > 5.0) doit annuler les votes BUY."""
    symbol = Symbol(name="frxXAUUSD", asset_class=AssetClass.COMMODITIES)
    portfolio = Portfolio(initial_capital=Decimal("10000.0"))

    features = {
        "ema_50": 2000.0,
        "rsi": 25.0,
        "spread": 6.0,  # LiquidityAgent vote WAIT (conf 0.9)
    }
    latest_prices = {symbol: Decimal("2050.0")}

    context = MarketContext(
        symbol=symbol,
        features=features,
        portfolio=portfolio,
        latest_prices=latest_prices,
    )

    agents = [TrendAgent(), MomentumAgent(), LiquidityAgent()]
    council = MultiAgentCouncil(agents=agents)

    verdict = council.evaluate(context)

    assert verdict.final_vote == "WAIT"
    assert verdict.position_size_multiplier == 0.0
    assert verdict.veto_reason is not None
    assert "LiquidityAgent" in verdict.veto_reason
