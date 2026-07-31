"""
Policy Trainer. Orchestrates the asynchronous, offline batch learning process.
"""

from typing import List, Dict, Any
from aegis_trade.domain.rl import ITrainingEnvironment, IPolicyStore


class PolicyTrainer:
    """
    Manages the lifecycle of an RL policy training session.
    Never run in the critical path (HFT execution loop).
    """

    def __init__(self, env: ITrainingEnvironment, policy_store: IPolicyStore):
        self.env = env
        self.policy_store = policy_store

    def train(self, total_timesteps: int, model_id: str) -> None:
        """
        Executes a training run and saves the resulting policy.
        """
        # Emits PolicyTrainingStarted event (Implementation detail depending on EventBus usage)
        
        print(f"Starting policy training for {total_timesteps} timesteps...")
        trained_model_id = self.env.train_policy(total_timesteps)
        
        # Emits PolicyTrainingCompleted event
        
        print(f"Training complete. Model saved with ID: {trained_model_id}")
