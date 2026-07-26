import logging
from aegis_trade.infrastructure.data.registry import ProviderRegistry

# These imports are fine here since bootstrap is responsible for wiring up dependencies
from aegis_trade.infrastructure.data.providers.openbb_provider import OpenBBDataProvider

logger = logging.getLogger(__name__)

def bootstrap_providers() -> None:
    """
    Registers all known data providers into the ProviderRegistry.
    This should be called exactly once during the application startup.
    """
    logger.info("Bootstrapping data providers...")
    ProviderRegistry.register("openbb", OpenBBDataProvider)
    # Future providers will be registered here (e.g., qlib, binance, polygon)
    # ProviderRegistry.register("qlib", QlibDataProvider)
    # ProviderRegistry.register("polygon", PolygonDataProvider)
    logger.info("Data providers bootstrapped successfully.")
