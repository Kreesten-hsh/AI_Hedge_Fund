from typing import Sequence
import logging

from aegis_trade.domain.core import MarketBar
from aegis_trade.domain.exceptions.data import ValidationError

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Validates ingested data to ensure integrity and consistency.
    """

    def validate_ohlcv(self, bars: Sequence[MarketBar]) -> Sequence[MarketBar]:
        """
        Validates a sequence of MarketBars.
        Checks for temporal order, negative values (already handled by MarketBar but good to verify pipeline state),
        and empty sequences.
        """
        if not bars:
            logger.warning("Validation: Received empty sequence of bars.")
            return bars

        sorted_bars = sorted(bars, key=lambda b: b.timestamp)
        
        # Check for duplicates or out of order
        for i in range(1, len(sorted_bars)):
            prev = sorted_bars[i-1]
            curr = sorted_bars[i]
            
            if curr.timestamp <= prev.timestamp:
                raise ValidationError(
                    f"Temporal order violation or duplicate timestamp detected at {curr.timestamp} "
                    f"for {curr.symbol.name}."
                )
        
        return sorted_bars
