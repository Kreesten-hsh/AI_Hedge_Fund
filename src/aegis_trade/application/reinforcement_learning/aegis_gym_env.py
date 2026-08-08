"""
Custom Gym Environment for Aegis Quant OS.
Simulates batch experience replay for RL training.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Any, Dict, List, Tuple

from aegis_trade.application.reinforcement_learning.reward_calculator import RewardCalculator


class CustomAegisEnv(gym.Env):
    """
    A Gym Environment that does not simulate a market tick-by-tick.
    Instead, it iterates over a batch of past experiences (Research Logbook)
    and trains the agent to output the optimal council weights to maximize
    the custom reward function.
    """
    
    def __init__(self, experiences: List[Dict[str, Any]], reward_calculator: RewardCalculator):
        super(CustomAegisEnv, self).__init__()
        
        self.experiences = experiences
        self.reward_calculator = reward_calculator
        self.current_step = 0
        self.max_steps = len(experiences)
        
        # Action space: 
        # Primary: risk_multiplier (0.0 to 2.0), confidence_threshold_adjustment (-0.5 to 0.5)
        # Secondary: 8 agent weights (Trend, Momentum, Volatility, Liquidity, Pattern, News, Portfolio, Execution) (0.0 to 1.0)
        # Total: 10 continuous values
        self.action_space = spaces.Box(
            low=np.array([0.0, -0.5] + [0.0]*8, dtype=np.float32),
            high=np.array([2.0, 0.5] + [1.0]*8, dtype=np.float32),
            dtype=np.float32
        )
        
        # Observation space: Let's assume the experience vector (from FAISS/Reflection Engine) 
        # has 25 dimensions (market features) + 5 dimensions (knowledge base aggregated scores). Total 30.
        # We use a dummy dimension size here. In reality, it matches the size of the combined state vector.
        self.obs_dim = 30
        self.observation_space = spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(self.obs_dim,), 
            dtype=np.float32
        )

    def reset(self, seed: int | None = None, options: dict[str, Any] | None = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.current_step = 0
        if self.max_steps == 0:
            return np.zeros(self.obs_dim, dtype=np.float32), {}
            
        return self._get_observation(), {}

    def _get_observation(self) -> np.ndarray:
        # Extract the observation from the current experience
        exp = self.experiences[self.current_step]
        # In a real implementation, this parses the `exp` dict into the 30-dim vector.
        # Here we mock it.
        obs = exp.get("features", np.zeros(self.obs_dim, dtype=np.float32))
        return np.array(obs, dtype=np.float32)

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        if self.current_step >= self.max_steps:
            return np.zeros(self.obs_dim, dtype=np.float32), 0.0, True, False, {}
            
        exp = self.experiences[self.current_step]
        
        # Simulated logic: Apply the action to the experience to estimate the reward.
        # In reality, we evaluate how well this `action` (these weights) would have performed
        # for this specific experience. Since we can't change the past, this step is tricky in off-policy
        # or offline RL. For our MVP, we calculate the reward based on the historical outcome,
        # perhaps adjusting the PnL/drawdown based on the suggested `risk_multiplier`.
        
        risk_multiplier = float(action[0])
        
        # Fetch metrics from experience
        pnl = exp.get("pnl", 0.0) * risk_multiplier
        capital = exp.get("capital", 1000.0)
        max_drawdown = exp.get("max_drawdown", 0.0) * risk_multiplier
        max_allowed_drawdown = exp.get("max_allowed_drawdown", 20.0)
        
        duration = exp.get("duration", 0.0)
        expected_duration = exp.get("expected_duration", 60.0)
        expected_price = exp.get("expected_price", 100.0)
        execution_price = exp.get("execution_price", 100.0)
        side = exp.get("side", "long")
        spread = exp.get("spread", 0.1)
        variance = exp.get("variance", 0.0)
        expected_profit = exp.get("expected_profit", 1.0) * risk_multiplier
        risk_amount = exp.get("risk_amount", 1.0) * risk_multiplier

        reward = self.reward_calculator.calculate(
            pnl=pnl,
            capital=capital,
            max_drawdown=max_drawdown,
            max_allowed_drawdown=max_allowed_drawdown,
            duration_seconds=duration,
            expected_duration=expected_duration,
            expected_price=expected_price,
            execution_price=execution_price,
            side=side,
            spread=spread,
            variance=variance,
            expected_profit=expected_profit,
            risk_amount=risk_amount
        )
        
        self.current_step += 1
        
        done = self.current_step >= self.max_steps
        info = {"reward": reward}
        
        if done:
            next_obs = np.zeros(self.obs_dim, dtype=np.float32)
        else:
            next_obs = self._get_observation()
            
        return next_obs, reward, done, False, info
