import math
from typing import Sequence
from datetime import timezone

from aegis_trade.domain import MarketBar, Tick
from aegis_trade.core.exceptions import InvalidMarketBar, InvalidTick

class StrictDataValidator:
    """
    S'assure que les données converties respectent rigoureusement les règles métier 
    et l'intégrité de la série temporelle.
    """

    def validate_bars(self, bars: Sequence[MarketBar]) -> Sequence[MarketBar]:
        if not bars:
            return bars

        previous_timestamp = None

        for bar in bars:
            # 1. Aucun None
            if any(val is None for val in (bar.open, bar.high, bar.low, bar.close, bar.volume)):
                raise InvalidMarketBar("MarketBar contains None values.")

            # 2. Aucun NaN (Decimal(NaN) lève ValueError à la création mais s'il est injecté par bypass, on le bloque)
            if any(math.isnan(float(val)) for val in (bar.open, bar.high, bar.low, bar.close, bar.volume)):
                raise InvalidMarketBar("MarketBar contains NaN values.")

            # 3. Timestamps UTC
            if bar.timestamp.tzinfo != timezone.utc:
                raise InvalidMarketBar("MarketBar timestamp must be UTC.")

            # 4. Monotonie stricte (croissant et pas de doublons)
            if previous_timestamp is not None:
                if bar.timestamp <= previous_timestamp:
                    raise InvalidMarketBar(f"MarketBars must be strictly chronologically ordered without duplicates. Found {bar.timestamp} after {previous_timestamp}")
            previous_timestamp = bar.timestamp

            # 5. Cohérence des prix
            if bar.high < bar.open or bar.high < bar.close:
                raise InvalidMarketBar(f"MarketBar High ({bar.high}) cannot be strictly lower than Open ({bar.open}) or Close ({bar.close}).")
            if bar.low > bar.open or bar.low > bar.close:
                raise InvalidMarketBar(f"MarketBar Low ({bar.low}) cannot be strictly higher than Open ({bar.open}) or Close ({bar.close}).")
            if bar.volume < 0:
                raise InvalidMarketBar(f"MarketBar volume ({bar.volume}) cannot be negative.")

        return bars
        
    def validate_ticks(self, ticks: Sequence[Tick]) -> Sequence[Tick]:
        if not ticks:
            return ticks

        previous_timestamp = None

        for tick in ticks:
            if tick.bid is None or tick.ask is None:
                raise InvalidTick("Tick contains None values.")
            if math.isnan(float(tick.bid)) or math.isnan(float(tick.ask)):
                raise InvalidTick("Tick contains NaN values.")

            if tick.timestamp.tzinfo != timezone.utc:
                raise InvalidTick("Tick timestamp must be UTC.")

            # Note: Pour les ticks, il peut y avoir plusieurs événements dans la même milliseconde/seconde
            # On vérifie seulement que ça ne recule pas. (timestamps >= précédents)
            if previous_timestamp is not None:
                if tick.timestamp < previous_timestamp:
                    raise InvalidTick(f"Ticks must be chronologically ordered. Found {tick.timestamp} after {previous_timestamp}")
            previous_timestamp = tick.timestamp

            if tick.bid > tick.ask:
                raise InvalidTick(f"Tick Bid ({tick.bid}) cannot be strictly higher than Ask ({tick.ask}).")

        return ticks
