from contracts.data_provider import DataProvider
from aegis_trade.providers.mt5_provider import MT5Provider
from aegis_trade.providers.replay_provider import ReplayProvider

class ProviderFactory:
    """
    Usine permettant d'instancier les fournisseurs de données.
    """

    @staticmethod
    def create(provider_type: str, **kwargs) -> DataProvider:
        provider_type = provider_type.lower()
        if provider_type == "mt5":
            return MT5Provider()
        elif provider_type == "replay":
            return ReplayProvider(
                bars=kwargs.get("bars", ()),
                ticks=kwargs.get("ticks", ())
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
