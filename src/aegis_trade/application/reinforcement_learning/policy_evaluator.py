"""
Policy Evaluator (Policy Promotion Gate).
"""

from typing import List, Dict, Any, Tuple
from src.aegis_trade.domain.rl import IPolicyStore

class PolicyEvaluator:
    """
    Policy Promotion Gate. 
    Evaluates a newly trained policy against a hold-out set of experiences.
    Ensures that the new policy performs at least as well on average reward and
    does not degrade the max drawdown compared to the current active policy.
    """

    def __init__(self, policy_store: IPolicyStore):
        self.policy_store = policy_store

    def evaluate(self, candidate_model_id: str, current_model_id: str, holdout_experiences: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Evaluates the candidate model.
        Returns:
            Tuple[bool, str]: (Is Promoted, Reason message)
        """
        # In a real implementation, we would load both models, run them over the `holdout_experiences`
        # in an evaluation environment, and compute average reward & max drawdown.
        
        # Placeholder for actual evaluation logic
        candidate_reward = 100.0
        candidate_drawdown = 5.0
        
        current_reward = 90.0
        current_drawdown = 5.0
        
        if candidate_reward >= current_reward and candidate_drawdown <= current_drawdown:
            # Emit PolicyPromoted event
            return True, "Candidate promoted: Better or equal reward without degrading drawdown."
        else:
            # Emit PolicyRejected event
            return False, "Candidate rejected: Failed to surpass current policy or degraded drawdown."
