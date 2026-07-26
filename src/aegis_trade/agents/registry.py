from typing import List, Dict, Type
from aegis_trade.agents.base import ResearchAgent

class AgentRegistry:
    """
    Registry for tracking and discovering available Research Agents.
    """
    def __init__(self):
        self._agents: Dict[str, ResearchAgent] = {}

    def register(self, agent: ResearchAgent) -> None:
        """Register an agent by its capability."""
        if agent.capability in self._agents:
            raise ValueError(f"Agent with capability '{agent.capability}' is already registered.")
        self._agents[agent.capability] = agent

    def get_by_capability(self, capability: str) -> ResearchAgent:
        """Retrieve a specific agent by its capability."""
        if capability not in self._agents:
            raise KeyError(f"No agent registered for capability '{capability}'.")
        return self._agents[capability]

    def list_agents(self) -> List[ResearchAgent]:
        """Return all registered agents."""
        return list(self._agents.values())

    def capabilities(self) -> List[str]:
        """Return a list of all registered capabilities."""
        return list(self._agents.keys())
