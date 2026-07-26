import os
from aegis_trade.agents.base import ResearchAgent

# ============================================================================
# AVERTISSEMENT DE DISCIPLINE SCIENTIFIQUE
# Hypothèse en phase Implémentation — non validée statistiquement.
# Ne pas utiliser en Council/Portfolio tant que la Mission C n'a pas produit un verdict IC.
# ============================================================================

class MacroAnalyst:
    """
    Macro Analyst Agent.
    Evaluates global macro indicators (e.g. DXY, US10Y) to deduce a macro bias for the traded asset.
    """
    def __init__(self, prompt_path: str = None):
        self._prompt_path = prompt_path

    @property
    def capability(self) -> str:
        return "macro_analysis"

    @property
    def prompt_path(self) -> str:
        if self._prompt_path:
            return self._prompt_path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        return os.path.join(base_dir, "prompts", "macro_v1.md")
