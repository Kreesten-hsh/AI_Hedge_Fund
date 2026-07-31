"""
Tests for Policy Trainer.
"""

from unittest.mock import MagicMock
from aegis_trade.application.reinforcement_learning.policy_trainer import PolicyTrainer
from aegis_trade.domain.rl import ITrainingEnvironment, IPolicyStore


def test_policy_trainer_orchestration():
    mock_env = MagicMock(spec=ITrainingEnvironment)
    mock_env.train_policy.return_value = "model_123"
    
    mock_store = MagicMock(spec=IPolicyStore)
    
    trainer = PolicyTrainer(env=mock_env, policy_store=mock_store)
    
    trainer.train(total_timesteps=1000, model_id="candidate_1")
    
    mock_env.train_policy.assert_called_once_with(1000)
