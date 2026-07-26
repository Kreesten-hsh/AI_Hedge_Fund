from aegis_trade.infrastructure.llm.adapters.base import ILLMProvider
from aegis_trade.infrastructure.llm.settings import LLMSettings

class MockAdapter(ILLMProvider):
    """
    Mock adapter for testing purposes.
    """
    
    def __init__(self, settings: LLMSettings):
        self.settings = settings
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Returns a mock response based on the format setting.
        """
        if self.settings.format == "json":
            return '{"decision": "hold", "confidence": 0.5, "multiplier": 1.0, "reasoning": "Mocked JSON response"}'
        return "Mocked text response"
