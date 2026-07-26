from typing import Protocol

class ResearchAgent(Protocol):
    """
    Stateless Protocol for all Research Agents.
    The agent defines its capability and prompt path, delegating all execution to the Runner.
    """
    
    @property
    def capability(self) -> str:
        """The specific domain this agent analyzes (e.g., 'regime', 'risk')."""
        ...
        
    @property
    def prompt_path(self) -> str:
        """Path to the markdown file containing the prompt template."""
        ...
