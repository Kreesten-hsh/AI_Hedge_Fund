from aegis_trade.infrastructure.llm.settings import LLMSettings
from aegis_trade.infrastructure.llm.adapters.base import ILLMProvider
from aegis_trade.infrastructure.llm.adapters.ollama_adapter import OllamaAdapter
from aegis_trade.infrastructure.llm.adapters.mock_adapter import MockAdapter
from aegis_trade.exceptions import ConfigurationError

class LLMProviderFactory:
    """
    Factory for instantiating the correct LLM adapter based on settings.
    """
    
    @staticmethod
    def create(settings: LLMSettings) -> ILLMProvider:
        provider_name = settings.provider.lower()
        
        if provider_name == "ollama":
            return OllamaAdapter(settings)
        elif provider_name == "mock":
            return MockAdapter(settings)
        else:
            raise ConfigurationError(f"Unsupported LLM provider: {provider_name}")
