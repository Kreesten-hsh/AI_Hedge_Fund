from typing import Dict, Type

from aegis_trade.domain.ports.data_provider import IDataProvider

class ProviderRegistry:
    """
    Registry for instantiating data providers dynamically.
    Avoids hardcoding if/else blocks and allows easy scaling to new providers 
    like Yahoo, Polygon, Binance, Kraken, AlphaVantage, etc.
    """

    _registry: Dict[str, Type[IDataProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: Type[IDataProvider]) -> None:
        """Registers a provider class under a specific name."""
        cls._registry[name.lower()] = provider_cls

    @classmethod
    def get(cls, name: str, **kwargs) -> IDataProvider:
        """Instantiates and returns the requested provider."""
        provider_cls = cls._registry.get(name.lower())
        if not provider_cls:
            from aegis_trade.domain.exceptions.data import ConfigurationError
            raise ConfigurationError(f"Provider '{name}' not found in registry. Did you forget to register it?")
        return provider_cls(**kwargs)
