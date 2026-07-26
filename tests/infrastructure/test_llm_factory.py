import pytest
from unittest.mock import Mock
from aegis_trade.infrastructure.llm.settings import LLMSettings
from aegis_trade.infrastructure.llm.factory import LLMProviderFactory
from aegis_trade.infrastructure.llm.adapters.ollama_adapter import OllamaAdapter
from aegis_trade.infrastructure.llm.adapters.mock_adapter import MockAdapter
from aegis_trade.exceptions import ConfigurationError

def test_factory_creates_ollama_adapter():
    settings = Mock(spec=LLMSettings)
    settings.provider = "ollama"
    
    adapter = LLMProviderFactory.create(settings)
    assert isinstance(adapter, OllamaAdapter)
    assert adapter.settings == settings

def test_factory_creates_mock_adapter():
    settings = Mock(spec=LLMSettings)
    settings.provider = "mock"
    
    adapter = LLMProviderFactory.create(settings)
    assert isinstance(adapter, MockAdapter)
    assert adapter.settings == settings

def test_factory_unsupported_provider():
    settings = Mock(spec=LLMSettings)
    settings.provider = "unknown"
    
    with pytest.raises(ConfigurationError, match="Unsupported LLM provider: unknown"):
        LLMProviderFactory.create(settings)
