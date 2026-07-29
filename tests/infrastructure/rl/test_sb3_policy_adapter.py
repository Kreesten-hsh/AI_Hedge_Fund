"""
Tests for SB3 Policy Adapter.
"""

from unittest.mock import MagicMock, patch
import pytest
import numpy as np

# Mock stable_baselines3 to avoid actual torch/SB3 initialization during unit tests
import sys
sys.modules['stable_baselines3'] = MagicMock()
sys.modules['stable_baselines3.common.env_util'] = MagicMock()
sys.modules['stable_baselines3.common.vec_env'] = MagicMock()

from src.aegis_trade.infrastructure.rl.sb3_policy_adapter import SB3PolicyAdapter
from src.aegis_trade.domain.rl import IPolicyStore


def test_sb3_adapter_initialization():
    mock_env = MagicMock()
    mock_store = MagicMock(spec=IPolicyStore)
    
    adapter = SB3PolicyAdapter(gym_env=mock_env, policy_store=mock_store)
    
    assert adapter.gym_env == mock_env
    assert adapter.policy_store == mock_store


@patch("src.aegis_trade.infrastructure.rl.sb3_policy_adapter.PPO")
def test_sb3_adapter_train(mock_ppo):
    mock_env = MagicMock()
    mock_store = MagicMock(spec=IPolicyStore)
    
    adapter = SB3PolicyAdapter(gym_env=mock_env, policy_store=mock_store)
    
    # Run training
    model_id = adapter.train_policy(100)
    
    assert "ppo_aegis_" in model_id
    adapter.model.learn.assert_called_once_with(total_timesteps=100)
    adapter.model.save.assert_called_once()
    mock_store.save_policy.assert_called_once()
