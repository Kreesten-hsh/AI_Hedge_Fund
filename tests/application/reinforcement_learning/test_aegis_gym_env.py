"""
Tests for Custom Aegis Env.
"""

import numpy as np
from aegis_trade.application.reinforcement_learning.aegis_gym_env import CustomAegisEnv
from aegis_trade.application.reinforcement_learning.reward_calculator import RewardCalculator


def test_env_initialization():
    experiences = [{"features": np.random.rand(30), "pnl": 1.0}]
    reward_calc = RewardCalculator()
    env = CustomAegisEnv(experiences, reward_calc)
    
    assert env.action_space.shape == (10,)
    assert env.observation_space.shape == (30,)
    assert env.max_steps == 1


def test_env_step_and_reset():
    experiences = [
        {"features": np.random.rand(30), "pnl": 5.0, "max_drawdown": 2.0},
        {"features": np.random.rand(30), "pnl": -2.0, "max_drawdown": 5.0}
    ]
    env = CustomAegisEnv(experiences, RewardCalculator())
    
    obs, info = env.reset()
    assert obs.shape == (30,)
    
    # Take an action
    action = env.action_space.sample()
    next_obs, reward, done, truncated, info = env.step(action)
    
    assert not done
    assert "reward" in info
    
    # Second step should terminate
    next_obs, reward, done, truncated, info = env.step(action)
    assert done
