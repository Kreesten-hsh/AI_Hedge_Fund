"""Adaptateurs Deriv.

`DerivMarketGateway` est la seule source de prix réels du système : avant lui,
aucun `subscribe`, aucun tick, aucune cotation n'entrait dans le pipeline.
"""

from aegis_trade.providers.deriv.market_gateway import (
    DerivMarketGateway,
    DerivProtocolError,
)

__all__ = ["DerivMarketGateway", "DerivProtocolError"]
