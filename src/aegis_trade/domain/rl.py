"""
Domain objects for Reinforcement Learning (AI-04).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Protocol
import uuid


@dataclass(kw_only=True)
class RewardComponents:
    """
    Detailed breakdown of the reward components for a given step.
    This corresponds to the RL_LEARNING_SPEC.md requirements.
    """
    pnl_normalise: float
    drawdown_penalty: float
    time_in_position_penalty: float
    slippage_penalty: float
    spread_penalty: float
    variance_penalty: float
    risk_reward_bonus: float

    @property
    def total_reward(self) -> float:
        """
        The final reward computed as:
        Reward = PnL - Penalties + Bonus
        """
        return (
            self.pnl_normalise 
            - self.drawdown_penalty 
            - self.time_in_position_penalty 
            - self.slippage_penalty 
            - self.spread_penalty 
            - self.variance_penalty 
            + self.risk_reward_bonus
        )


@dataclass(kw_only=True)
class PolicyDecision:
    """
    The output of the RL Policy (Action Space).
    It adjusts global risk parameters and (eventually) the multi-agent council weights.
    """
    # Primary interface (AI-04)
    risk_multiplier: float
    confidence_threshold_adjustment: float
    
    # Secondary interface (prepared for AI-05)
    agent_weights: Dict[str, float] = field(default_factory=dict)


@dataclass(kw_only=True)
class RlExperienceBatch:
    """
    A batch of experiences for the RL Environment to replay.
    """
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    experiences: list[Any] = field(default_factory=list)


# --- Interfaces (Ports) ---

class IPolicyStore(Protocol):
    """
    Interface for saving and loading RL policy weights/models.
    """
    def save_policy(self, model_id: str, path: str) -> None:
        ...

    def load_policy(self, model_id: str) -> Any:
        ...


class ITrainingEnvironment(Protocol):
    """
    Abstract representation of the RL Environment to decouple domain from Gym/SB3.
    """
    def reset(self) -> Any:
        ...

    def step(self, action: Any) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        ...

    def train_policy(self, total_timesteps: int) -> str:
        """
        Train the policy and return the model_id of the newly trained policy.
        """
        ...
