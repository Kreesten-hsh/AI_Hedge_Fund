"""
Policy Checkpoint Store.
Handles the persistence of trained RL models (.zip files).
"""

import os
import shutil
from typing import Any
from stable_baselines3 import PPO

from src.aegis_trade.domain.rl import IPolicyStore

class PolicyCheckpointStore(IPolicyStore):
    """
    Saves and loads policy checkpoints. 
    Aligns with the versioning style of KnowledgeVersion.
    """

    def __init__(self, storage_dir: str = ".data/rl_models"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def save_policy(self, model_id: str, source_path: str) -> None:
        """
        Moves the model from the source_path to the permanent storage_dir.
        """
        dest_path = os.path.join(self.storage_dir, f"{model_id}.zip")
        shutil.copy2(source_path, dest_path)
        print(f"Policy {model_id} saved to {dest_path}")

    def load_policy(self, model_id: str) -> Any:
        """
        Loads the PPO model from storage.
        """
        path = os.path.join(self.storage_dir, f"{model_id}.zip")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Policy file {path} not found.")
            
        # Hardcoding PPO for MVP. In a more flexible setup, this could read metadata to determine algo.
        model = PPO.load(path, device="cpu")
        return model
