from aegis_trade.agents.base import ResearchAgent
import os

class RegimeAnalyst:
    """
    Stateless descriptor for the Regime Analyst.
    All execution logic is handled by the AgentRunner.
    """
    @property
    def capability(self) -> str:
        return "regime"
        
    @property
    def prompt_path(self) -> str:
        # Resolve path relative to this file to ensure it finds the prompt
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "prompts", "regime_v1.md")
