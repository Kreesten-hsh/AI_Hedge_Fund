import os
from aegis_trade.agents.base import ResearchAgent

class RiskAnalyst:
    """
    Risk Analyst Agent.
    Evaluates local asset volatility (ATR, standard deviation) to suggest a position multiplier.
    """
    def __init__(self, prompt_path: str = None):
        self._prompt_path = prompt_path

    @property
    def capability(self) -> str:
        return "risk_analysis"

    @property
    def prompt_path(self) -> str:
        if self._prompt_path:
            return self._prompt_path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        return os.path.join(base_dir, "prompts", "risk_v1.md")
