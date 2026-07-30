"""
Policy Checkpoint Store.
Handles the persistence of trained RL models (.zip files).
"""

import os
import shutil
import json
import logging
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict
from stable_baselines3 import PPO

logger = logging.getLogger(__name__)

from aegis_trade.domain.rl import IPolicyStore

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

    def promote_to_active(self, model_id: str, metrics: Dict[str, Any]) -> None:
        """
        Atomically writes the active_policy.json metadata file.
        """
        meta_path = os.path.join(self.storage_dir, "active_policy.json")
        data = {
            "model_id": model_id,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics
        }
        
        # Atomic write
        fd, temp_path = tempfile.mkstemp(dir=self.storage_dir, prefix="active_", suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=4)
            # Rename is atomic on POSIX
            os.replace(temp_path, meta_path)
            logger.info(f"Policy {model_id} promoted to active.")
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def load_active_policy(self) -> Any:
        """
        Loads the active policy. If none exists or fails, returns None and logs a warning.
        """
        meta_path = os.path.join(self.storage_dir, "active_policy.json")
        if not os.path.exists(meta_path):
            logger.warning(f"No active_policy.json found at {meta_path}. Falling back to default policy.")
            return None
            
        try:
            with open(meta_path, "r") as f:
                data = json.load(f)
            model_id = data.get("model_id")
            if not model_id:
                logger.warning("active_policy.json is missing 'model_id'. Falling back.")
                return None
            return self.load_policy(model_id)
        except Exception as e:
            logger.warning(f"Failed to load active policy: {e}. Falling back.")
            return None
