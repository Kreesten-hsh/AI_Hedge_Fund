"""
Stable-Baselines3 Policy Adapter.
Encapsulates FinRL/SB3 complexity. Implements ITrainingEnvironment.
"""

from typing import Any
import os
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv

from src.aegis_trade.domain.rl import ITrainingEnvironment, IPolicyStore


class SB3PolicyAdapter(ITrainingEnvironment):
    """
    Adapter bridging our Domain's ITrainingEnvironment with Stable-Baselines3.
    """

    def __init__(self, gym_env: Any, policy_store: IPolicyStore, model_id_prefix: str = "ppo_aegis"):
        # We assume gym_env is an instance of our CustomAegisEnv
        self.gym_env = gym_env
        self.policy_store = policy_store
        self.model_id_prefix = model_id_prefix
        
        # Wrap environment
        self.vec_env = DummyVecEnv([lambda: self.gym_env])
        
        # Initialize PPO model
        self.model = PPO(
            "MlpPolicy", 
            self.vec_env, 
            verbose=1,
            device="cpu"  # Explicitly force CPU as per constraints
        )

    def reset(self) -> Any:
        return self.gym_env.reset()

    def step(self, action: Any) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        return self.gym_env.step(action)

    def train_policy(self, total_timesteps: int) -> str:
        """
        Train the SB3 PPO model and save it via the PolicyStore.
        """
        self.model.learn(total_timesteps=total_timesteps)
        
        # Generate a model ID (e.g., using a timestamp or UUID)
        import uuid
        model_id = f"{self.model_id_prefix}_{uuid.uuid4().hex[:8]}"
        
        # SB3 uses its own save method, so we save to a temporary path,
        # then the store takes over, or we just pass the path to the store.
        # For simplicity, we let the policy store manage the directory, 
        # and we pass it the model object to save. Wait, IPolicyStore takes model_id and path.
        # Let's define a standardized path pattern.
        temp_path = f"/tmp/{model_id}.zip"
        self.model.save(temp_path)
        
        self.policy_store.save_policy(model_id, temp_path)
        
        # Cleanup temporary zip
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return model_id
