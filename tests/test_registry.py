import pytest
from aegis_trade.infrastructure.data.registry import ProviderRegistry
from aegis_trade.domain.exceptions.data import ConfigurationError

def test_registry_missing_provider_raises_error():
    with pytest.raises(ConfigurationError, match="not found in registry"):
        ProviderRegistry.get("non_existent_provider")

def test_registry_successful_registration():
    class DummyProvider:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            
    ProviderRegistry.register("dummy", DummyProvider)
    instance = ProviderRegistry.get("dummy", my_arg="test")
    
    assert isinstance(instance, DummyProvider)
    assert instance.kwargs == {"my_arg": "test"}
