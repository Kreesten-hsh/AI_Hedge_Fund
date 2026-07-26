from abc import ABC, abstractmethod
from typing import Dict, Any

class ILLMProvider(ABC):
    """
    Abstract interface for LLM Providers.
    Ensures that domain logic is decoupled from specific LLM implementations.
    """
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generates a response from the LLM.
        
        Args:
            prompt: The user prompt.
            system_prompt: Optional system instructions.
            
        Returns:
            The generated response string.
        """
        pass
