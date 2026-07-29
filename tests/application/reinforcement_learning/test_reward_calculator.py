"""
Tests for RL Reward Calculator.
"""

import pytest
from src.aegis_trade.application.reinforcement_learning.reward_calculator import RewardCalculator


def test_reward_penalizes_risky_small_win():
    """
    Test explicitly requested by CTO:
    A small win (e.g., $2) with a drawdown close to the stop loss (e.g. max drawdown allowed)
    should result in a heavily negative reward.
    """
    calculator = RewardCalculator(drawdown_penalty_weight=2.0)
    
    pnl = 2.0
    capital = 1000.0
    max_drawdown = 19.5  # Drawdown very close to the limit
    max_allowed_drawdown = 20.0
    
    # Calculate components manually or use the calculate method
    reward = calculator.calculate(
        pnl=pnl,
        capital=capital,
        max_drawdown=max_drawdown,
        max_allowed_drawdown=max_allowed_drawdown,
        duration_seconds=10,
        expected_duration=60,
        expected_price=100.0,
        execution_price=100.0,
        side="long",
        spread=0.01,
        variance=0.1,
        expected_profit=5.0,
        risk_amount=20.0
    )
    
    # Assert the reward is strongly negative due to exponential penalty
    assert reward < -10.0, f"Expected highly negative reward, got {reward}"


def test_reward_components():
    calculator = RewardCalculator()
    
    # PnL norm
    assert calculator.calc_pnl_normalized(100.0, 1000.0) == 10.0
    
    # Drawdown penalty
    pen = calculator.calc_drawdown_penalty(10.0, 20.0)
    assert pen > 0
    
    # Time in position
    assert calculator.calc_time_in_position_penalty(10, 60) == 0.0
    assert calculator.calc_time_in_position_penalty(120, 60) > 0.0
    
    # Slippage
    assert calculator.calc_slippage_penalty(100.0, 101.0, "long") > 0.0
    assert calculator.calc_slippage_penalty(100.0, 99.0, "short") > 0.0
    assert calculator.calc_slippage_penalty(100.0, 99.0, "long") == 0.0
    
    # Risk/Reward bonus
    bonus = calculator.calc_risk_reward_bonus(10.0, 5.0)
    assert bonus == 2.0 * calculator.risk_reward_bonus_weight
