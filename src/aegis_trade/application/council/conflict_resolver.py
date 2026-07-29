from typing import Tuple

class ConflictResolver:
    """
    Implements MULTI_AGENT_COUNCIL.md Section 4 logic.
    Reduces position size or aborts trade if disagreement is too high.
    """
    def __init__(self, high_disagreement_threshold: float = 0.8, abort_threshold: float = 0.95):
        self.high_disagreement_threshold = high_disagreement_threshold
        self.abort_threshold = abort_threshold

    def resolve(self, buy_score: float, sell_score: float) -> Tuple[float, float]:
        """
        Calculates the disagreement level and the position size multiplier.
        Returns: (position_size_multiplier, disagreement_level)
        """
        if buy_score == 0.0 and sell_score == 0.0:
            return 0.0, 0.0
            
        min_score = min(buy_score, sell_score)
        max_score = max(buy_score, sell_score)
        
        # Disagreement is the ratio of the minority vote to the majority vote
        disagreement_level = min_score / max_score if max_score > 0 else 0.0
        
        multiplier = 1.0
        
        if disagreement_level >= self.abort_threshold:
            multiplier = 0.0 # Trade is abandoned due to maximum uncertainty
        elif disagreement_level >= self.high_disagreement_threshold:
            multiplier = 0.25 # Position size is divided by 4
            
        return multiplier, disagreement_level
